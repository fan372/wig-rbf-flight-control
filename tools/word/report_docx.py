# -*- coding: utf-8 -*-
"""Pure standard-library Word (.docx) report generator for Chinese engineering
research reports.

Everything is written by hand with :mod:`zipfile` and string/XML templates --
no ``python-docx``, no third-party packages.  The result opens in Word 2016+
without a repair prompt.

Typical use::

    from report_docx import Report

    r = Report(title="报告标题", subtitle="副标题", author="作者", date="2026年9月")
    r.cover()
    r.toc()
    r.h1("1 引言")
    r.p(r"正文段落，行内公式写作 $\\alpha + \\beta$，自动转 OMML。")
    r.eq(r"\\dot{V} = \\frac{T\\cos\\alpha - D}{m} - g\\sin\\gamma", number="(1)")
    r.table(headers=["列1", "列2"], rows=[["a", "b"]], caption="表 1-1 参数表",
            widths=[6.0, 6.0])
    r.figure("fig.png", caption="图 1-1 仿真结果", width_cm=14.0)
    r.save("out.docx")

Running ``python report_docx.py`` emits ``report_demo.docx`` next to this file.

Units / page geometry (documented because Word twips cannot express 2.5 cm and
2.8 cm exactly):

* page: A4 = 11906 x 16838 twips
* margins: top/bottom **1440 twips** (2.540 cm, the 2.5 cm approximation),
  left/right **1588 twips** (2.8006 cm, the 2.8 cm approximation)
* usable text width: 8730 twips = 15.397 cm
* 1 cm = 567 twips = 360000 EMU
"""

from __future__ import annotations

import hashlib
import os
import struct
import zipfile
from datetime import datetime, timezone
from typing import Iterable, Sequence
from xml.sax.saxutils import escape

import omml
from omml import CM_TO_TWIPS, M_NS, W_NS

__all__ = ["Report", "split_math", "png_size", "jpeg_size", "image_size"]

# --------------------------------------------------------------------------
# Namespaces
# --------------------------------------------------------------------------

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'

# Relationship type URIs
RT_OFFICE_DOCUMENT = R_NS + "/officeDocument"
RT_CORE_PROPS = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
RT_EXT_PROPS = R_NS + "/extended-properties"
RT_STYLES = R_NS + "/styles"
RT_SETTINGS = R_NS + "/settings"
RT_NUMBERING = R_NS + "/numbering"
RT_FOOTER = R_NS + "/footer"
RT_IMAGE = R_NS + "/image"

# Content types
CT_DOCUMENT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
CT_STYLES = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"
CT_SETTINGS = "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"
CT_NUMBERING = "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"
CT_FOOTER = "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
CT_CORE = "application/vnd.openxmlformats-package.core-properties+xml"
CT_APP = "application/vnd.openxmlformats-officedocument.extended-properties+xml"

# Page geometry
A4_W_TW = 11906
A4_H_TW = 16838
MARGIN_TB_TW = 1440          # 2.5 cm approximated as 1 inch
MARGIN_LR_TW = 1588          # 2.8 cm approximated as 1588 twips
TEXT_W_TW = A4_W_TW - 2 * MARGIN_LR_TW      # 8730 twips
TEXT_W_CM = TEXT_W_TW / CM_TO_TWIPS          # 15.397 cm

CM_TO_EMU = 360000
EMU_PER_TWIP = 635           # 1 twip = 635 EMU

_HALF_PT = 0.5                # w:sz units are half-points
_SOF_MARKERS = frozenset(
    [0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF]
)

ACCEPTED_IMAGE_EXT = {"png": "image/png", "jpeg": "image/jpeg", "jpg": "image/jpeg"}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _esc(text: object) -> str:
    """XML-escape text content (``&``, ``<``, ``>``)."""
    return escape("" if text is None else str(text))


def _attr(value: object) -> str:
    """XML-escape a value for a double-quoted attribute."""
    return escape("" if value is None else str(value), {'"': "&quot;"})


def cm_to_twips(cm: float) -> int:
    return int(round(float(cm) * CM_TO_TWIPS))


def cm_to_emu(cm: float) -> int:
    return int(round(float(cm) * CM_TO_EMU))


def twips_to_cm(tw: float) -> float:
    return float(tw) / CM_TO_TWIPS


# --------------------------------------------------------------------------
# Image header parsing (struct only -- no PIL)
# --------------------------------------------------------------------------


def png_size(data: bytes) -> tuple[int, int]:
    """Return ``(width_px, height_px)`` from a PNG IHDR chunk."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file (bad signature)")
    if data[12:16] != b"IHDR":
        raise ValueError("not a PNG file (first chunk is not IHDR)")
    w, h = struct.unpack(">II", data[16:24])
    return int(w), int(h)


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Return ``(width_px, height_px)`` by scanning JPEG SOFn markers."""
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG file (bad SOI)")
    i, n = 2, len(data)
    while i < n - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0x01,) or 0xD0 <= marker <= 0xD8:
            continue
        if i + 2 > n:
            break
        seg_len = struct.unpack(">H", data[i:i + 2])[0]
        if marker in _SOF_MARKERS:
            if i + 7 > n:
                break
            h, w = struct.unpack(">HH", data[i + 3:i + 7])
            return int(w), int(h)
        i += max(seg_len, 2)
    raise ValueError("could not locate a SOFn marker in the JPEG data")


def image_size(data: bytes, path: str = "<bytes>") -> tuple[int, int, str, str]:
    """Return ``(width_px, height_px, extension, content_type)`` for PNG/JPEG."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = png_size(data)
        return w, h, "png", "image/png"
    if data[:2] == b"\xff\xd8":
        w, h = jpeg_size(data)
        return w, h, "jpeg", "image/jpeg"
    raise ValueError(f"unsupported image format for {path!r} (need PNG or JPEG)")


# --------------------------------------------------------------------------
# Inline math splitting
# --------------------------------------------------------------------------


def split_math(text: str) -> list[tuple[str, str]]:
    """Split ``text`` into ``[("text", s), ("math", latex), ...]``.

    ``$...$`` delimits inline math; ``\\$`` is a literal dollar sign.  An
    unterminated ``$`` is treated as literal text.
    """
    parts: list[tuple[str, str]] = []
    buf: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n and text[i + 1] == "$":
            buf.append("$")
            i += 2
            continue
        if ch == "$":
            j = text.find("$", i + 1)
            if j > i + 0 and j != -1:
                if buf:
                    parts.append(("text", "".join(buf)))
                    buf = []
                parts.append(("math", text[i + 1:j]))
                i = j + 1
                continue
            buf.append(ch)
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append(("text", "".join(buf)))
    return parts


# --------------------------------------------------------------------------
# Static XML parts
# --------------------------------------------------------------------------

_EMPTY_RELS = XML_DECL + f'<Relationships xmlns="{PKG_REL_NS}"/>'

_DOCUMENT_ROOT_OPEN = (
    XML_DECL
    + f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}" '
    f'xmlns:wp="{WP_NS}" xmlns:a="{A_NS}" xmlns:pic="{PIC_NS}">'
)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


class Report:
    """Incremental builder for a single ``.docx`` report.

    All content methods append to an in-memory body; :meth:`save` writes the
    complete OPC package.
    """

    #: default caption / note sizes (pt)
    CAPTION_PT = 10.5
    NOTE_PT = 9.0

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        author: str = "",
        date: str = "",
        ascii_font: str = "Times New Roman",
        east_font: str = "宋体",
        heading_east_font: str = "黑体",
        accent: str = "1F4E79",
        body_size_pt: float = 12.0,
        line_spacing: float = 1.5,
        math_font: str = "Cambria Math",
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.author = author
        self.date = date
        self.ascii_font = ascii_font
        self.east_font = east_font
        self.heading_east_font = heading_east_font
        self.accent = accent.lstrip("#").upper()
        self.body_size_pt = float(body_size_pt)
        self.line_spacing = float(line_spacing)
        self.math_font = math_font

        self.text_width_cm = TEXT_W_CM
        self.warnings: list[str] = []

        # body / state
        self._blocks: list[str] = []
        self._last_kind: str = ""
        self._current_list_num: int | None = None
        self._num_ids: list[int] = []

        # media / relationships
        self._images: list[dict] = []
        self._image_cache: dict[str, int] = {}
        self._next_rid = 5          # rId1..rId4 are reserved (styles/settings/numbering/footer)
        self._next_docpr = 1
        self._created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # low level run / paragraph builders
    # ------------------------------------------------------------------

    def _rfonts(self, ascii_font: str | None = None, east_font: str | None = None) -> str:
        a = ascii_font or self.ascii_font
        e = east_font or self.east_font
        return (
            f'<w:rFonts w:ascii="{_attr(a)}" w:hAnsi="{_attr(a)}" '
            f'w:eastAsia="{_attr(e)}" w:cs="{_attr(a)}" w:hint="eastAsia"/>'
        )

    def _rpr(
        self,
        size_pt: float | None = None,
        *,
        bold: bool = False,
        italic: bool = False,
        color: str | None = None,
        ascii_font: str | None = None,
        east_font: str | None = None,
        lang: bool = True,
    ) -> str:
        sz = int(round((size_pt if size_pt is not None else self.body_size_pt) * 2))
        out = ["<w:rPr>", self._rfonts(ascii_font, east_font)]
        if bold:
            out.append("<w:b/><w:bCs/>")
        if italic:
            out.append("<w:i/><w:iCs/>")
        if color:
            out.append(f'<w:color w:val="{_attr(color.lstrip("#").upper())}"/>')
        out.append(f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')
        if lang:
            out.append('<w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/>')
        out.append("</w:rPr>")
        return "".join(out)

    def _run(
        self,
        text: str,
        size_pt: float | None = None,
        *,
        bold: bool = False,
        italic: bool = False,
        color: str | None = None,
        ascii_font: str | None = None,
        east_font: str | None = None,
    ) -> str:
        rpr = self._rpr(
            size_pt,
            bold=bold,
            italic=italic,
            color=color,
            ascii_font=ascii_font,
            east_font=east_font,
        )
        return f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'

    def _runs_with_math(
        self,
        text: str,
        size_pt: float | None = None,
        *,
        bold: bool = False,
        italic: bool = False,
        color: str | None = None,
    ) -> str:
        """Runs for ``text`` with ``$...$`` spans turned into inline OMML."""
        out: list[str] = []
        for kind, chunk in split_math(text):
            if kind == "math":
                out.append(omml.inline_omml(chunk))
            elif chunk:
                out.append(
                    self._run(
                        chunk,
                        size_pt,
                        bold=bold,
                        italic=italic,
                        color=color,
                    )
                )
        if not out:
            out.append(self._run("", size_pt, bold=bold, italic=italic, color=color))
        return "".join(out)

    @staticmethod
    def _spacing(
        before: int = 0,
        after: int = 0,
        line: int | None = 360,
        rule: str = "auto",
    ) -> str:
        if line is None:
            return f'<w:spacing w:before="{before}" w:after="{after}"/>'
        return (
            f'<w:spacing w:before="{before}" w:after="{after}" '
            f'w:line="{line}" w:lineRule="{rule}"/>'
        )

    def _emit(self, xml: str, kind: str) -> None:
        self._blocks.append(xml)
        self._last_kind = kind
        if kind != "num":
            self._current_list_num = None

    # ------------------------------------------------------------------
    # cover / toc
    # ------------------------------------------------------------------

    def cover(self) -> None:
        """Title page: title, subtitle, author, date, then a page break."""
        blocks: list[str] = []
        blank_line = (
            "<w:p><w:pPr>"
            + self._spacing(0, 0)
            + '<w:jc w:val="center"/></w:pPr></w:p>'
        )
        for _ in range(4):
            blocks.append(blank_line)

        if self.title:
            blocks.append(
                "<w:p><w:pPr>"
                + self._spacing(0, 240)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                + '<w:jc w:val="center"/>'
                + "</w:pPr>"
                + self._run(
                    self.title,
                    26.0,
                    bold=True,
                    color=self.accent,
                    ascii_font=self.ascii_font,
                    east_font=self.heading_east_font,
                )
                + "</w:p>"
            )
        if self.subtitle:
            blocks.append(
                "<w:p><w:pPr>"
                + self._spacing(0, 120)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                + '<w:jc w:val="center"/>'
                + "</w:pPr>"
                + self._run(
                    self.subtitle,
                    16.0,
                    bold=False,
                    color="404040",
                    ascii_font=self.ascii_font,
                    east_font=self.heading_east_font,
                )
                + "</w:p>"
            )
        for _ in range(6):
            blocks.append(blank_line)

        for line, size in ((self.author, 14.0), (self.date, 14.0)):
            if not line:
                continue
            blocks.append(
                "<w:p><w:pPr>"
                + self._spacing(0, 120)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                + '<w:jc w:val="center"/>'
                + "</w:pPr>"
                + self._run(line, size, east_font=self.heading_east_font)
                + "</w:p>"
            )

        self._blocks.extend(blocks)
        self._last_kind = "cover"
        self._current_list_num = None
        self.pagebreak()

    def toc(self, title: str | None = "目录", *, page_break_after: bool = False) -> None:
        """Insert a real ``TOC \\o "1-3" \\h \\z \\u`` field.

        ``word/settings.xml`` carries ``<w:updateFields w:val="true"/>`` and the
        field char is marked ``w:dirty="true"``, so Word refreshes the table of
        contents when the document is opened (Word asks the user to confirm
        updating fields the first time).

        ``title=None`` suppresses the "目录" heading line above the field.
        """
        if title:
            self._emit(
                "<w:p><w:pPr>"
                '<w:keepNext/>'
                + self._spacing(0, 240)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                + '<w:jc w:val="center"/>'
                + "</w:pPr>"
                + self._run(
                    title,
                    16.0,
                    bold=True,
                    ascii_font=self.ascii_font,
                    east_font=self.heading_east_font,
                )
                + "</w:p>",
                "toc",
            )

        rpr = self._rpr(None)
        placeholder = (
            "请按 Ctrl+A 后按 F9，或右键选择“更新域”以生成目录。"
            "（Word 会在打开文档时自动更新）"
        )
        field = (
            "<w:p><w:pPr>"
            + self._spacing(0, 0)
            + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            + "</w:pPr>"
            f'<w:r>{rpr}<w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
            f'<w:r>{rpr}<w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
            f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(placeholder)}</w:t></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>'
            "</w:p>"
        )
        self._emit(field, "toc")
        if page_break_after:
            self.pagebreak()

    # ------------------------------------------------------------------
    # headings
    # ------------------------------------------------------------------

    def _heading(self, text: str, level: int, page_break_before: bool = False) -> None:
        style_id, size_pt, color = {
            1: ("Heading1", 16.0, self.accent),
            2: ("Heading2", 14.0, self.accent),
            3: ("Heading3", 12.5, None),
        }[level]
        ppr = (
            "<w:pPr>"
            f'<w:pStyle w:val="{style_id}"/>'
            "<w:keepNext/><w:keepLines/>"
        )
        if page_break_before:
            ppr += "<w:pageBreakBefore/>"
        ppr += (
            self._spacing(240, 120)
            + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            + '<w:jc w:val="left"/>'
            + "</w:pPr>"
        )
        run = f"<w:r>{self._rpr(size_pt, bold=True, color=color, east_font=self.heading_east_font)}" \
              f'<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'
        self._emit(f"<w:p>{ppr}{run}</w:p>", f"h{level}")

    def h1(self, text: str, page_break_before: bool = False) -> None:
        """Level-1 heading (style ``Heading1``, outline level 0)."""
        self._heading(text, 1, page_break_before)

    def h2(self, text: str, page_break_before: bool = False) -> None:
        """Level-2 heading (style ``Heading2``, outline level 1)."""
        self._heading(text, 2, page_break_before)

    def h3(self, text: str, page_break_before: bool = False) -> None:
        """Level-3 heading (style ``Heading3``, outline level 2)."""
        self._heading(text, 3, page_break_before)

    # ------------------------------------------------------------------
    # body paragraphs / lists
    # ------------------------------------------------------------------

    def p(
        self,
        text: str,
        first_indent: bool = True,
        align: str | None = None,
        *,
        size_pt: float | None = None,
        bold: bool = False,
    ) -> None:
        """Body paragraph.

        ``$...$`` spans become inline ``<m:oMath>`` in the same ``<w:p>``.
        ``first_indent=True`` sets the Chinese 2-character first line indent
        (``w:firstLineChars="200" w:firstLine="480"``).
        """
        jc = align if align else "both"
        ppr = "<w:pPr>" + self._spacing(0, 0)
        if first_indent:
            ppr += '<w:ind w:firstLineChars="200" w:firstLine="480"/>'
        else:
            ppr += '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
        ppr += f'<w:jc w:val="{_attr(jc)}"/></w:pPr>'
        self._emit(f"<w:p>{ppr}{self._runs_with_math(text, size_pt, bold=bold)}</w:p>", "p")

    def _list_para(self, text: str, num_id: int, ilvl: int, left: int, hanging: int) -> str:
        # NOTE: <w:numPr> must precede <w:spacing>/<w:ind>/<w:jc> in CT_PPrBase.
        ppr = (
            "<w:pPr>"
            f'<w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{num_id}"/></w:numPr>'
            + self._spacing(0, 0)
            + f'<w:ind w:left="{left}" w:hanging="{hanging}"/>'
            + '<w:jc w:val="both"/>'
            + "</w:pPr>"
        )
        return f"<w:p>{ppr}{self._runs_with_math(text)}</w:p>"

    def bullet(self, text: str, level: int = 0) -> None:
        """Bullet-list item (``numbering.xml`` ``numId`` 1, 4 levels)."""
        lvl = max(0, min(int(level), 3))
        self._emit(
            self._list_para(text, 1, lvl, 900 + 420 * lvl, 420),
            "bullet",
        )

    def num(self, text: str, level: int = 0) -> None:
        """Numbered list item.

        Each *contiguous group* of :meth:`num` calls gets its own ``w:numId``
        (all sharing one abstract numbering definition), so numbering restarts
        at 1 after any other block is emitted.  ``level`` is 0-based.
        """
        if self._current_list_num is None:
            self._current_list_num = 3 + len(self._num_ids)
            self._num_ids.append(self._current_list_num)
        lvl = max(0, min(int(level), 3))
        self._emit(
            self._list_para(text, self._current_list_num, lvl, 900 + 420 * lvl, 420),
            "num",
        )

    # ------------------------------------------------------------------
    # equations
    # ------------------------------------------------------------------

    def eq(self, latex: str, number: str | None = None, *, layout: str = "table") -> None:
        """Display equation.

        With ``number`` the equation sits in a borderless 1x2 table: column 1
        centres the equation, column 2 right-aligns the number.  Without a
        number the equation is simply a centred paragraph.  In both cases the
        paragraph has no first-line indent.
        """
        if number is None:
            eq = omml.display_omml(latex)
            ppr = (
                "<w:pPr>"
                + self._spacing(120, 120)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                + '<w:jc w:val="center"/>'
                + "</w:pPr>"
            )
            self._emit(f"<w:p>{ppr}{eq}</w:p>", "eq")
            return

        if layout == "tabs":
            self._emit(
                omml.omml_paragraph(
                    latex,
                    number=str(number),
                    text_width_cm=self.text_width_cm,
                    before=120,
                    after=120,
                ),
                "eq",
            )
            return

        self._emit(
            omml.equation_table(
                latex,
                str(number),
                text_width_cm=self.text_width_cm,
                before=120,
                after=120,
            ),
            "eq",
        )

    # ------------------------------------------------------------------
    # captions / notes
    # ------------------------------------------------------------------

    def caption(self, text: str, *, keep_next: bool = False, size_pt: float | None = None) -> None:
        """Standalone caption paragraph (centred, 10.5 pt, not bold)."""
        ppr = (
            "<w:pPr>"
            '<w:pStyle w:val="Caption"/>'
        )
        if keep_next:
            ppr += "<w:keepNext/>"
        ppr += (
            self._spacing(60, 60)
            + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            + '<w:jc w:val="center"/>'
            + "</w:pPr>"
        )
        run = self._run(text, size_pt if size_pt is not None else self.CAPTION_PT)
        self._emit(f"<w:p>{ppr}{run}</w:p>", "caption")

    def note(self, text: str, *, align: str = "left", size_pt: float | None = None) -> None:
        """Small-print annotation (9 pt by default)."""
        ppr = (
            "<w:pPr>"
            + self._spacing(0, 60, line=280)
            + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            + f'<w:jc w:val="{_attr(align)}"/>'
            + "</w:pPr>"
        )
        run = self._run(text, size_pt if size_pt is not None else self.NOTE_PT)
        self._emit(f"<w:p>{ppr}{run}</w:p>", "note")

    # ------------------------------------------------------------------
    # tables
    # ------------------------------------------------------------------

    def table(
        self,
        headers: Sequence[str] | None,
        rows: Iterable[Sequence[str]],
        caption: str | None = None,
        widths: Sequence[float] | None = None,
        font_size: float = 10.5,
        aligns: Sequence[str] | None = None,
        header_shade: str = "D9E2F3",
        header_bold: bool = True,
        first_col_align: str | None = None,
    ) -> None:
        """Full-bordered table with a caption **above** it.

        Parameters
        ----------
        headers
            Header row (``None`` for a header-less table).
        rows
            Iterable of row sequences.  Rows shorter than ``headers`` are
            padded, longer ones are truncated.
        caption
            Caption text placed in a paragraph above the table (keeps with it).
        widths
            Column widths in **cm**.  ``None`` distributes the text width
            evenly.  If the total exceeds the usable text width the widths are
            scaled down proportionally and a warning is recorded.
        font_size
            Cell text size in pt (default 10.5).
        aligns
            Per-column ``"left" | "center" | "right"`` applied to header and
            body cells (default: every column centred).
        header_shade
            Hex fill for the header row (default light blue ``D9E2F3``).
        first_col_align
            Optional override for column 0 (e.g. ``"left"``).
        """
        data_rows = [list(r) for r in rows]
        ncols = len(headers) if headers is not None else (len(data_rows[0]) if data_rows else 0)
        if ncols == 0:
            raise ValueError("Report.table: need at least one column (headers or rows)")

        if widths is None:
            col_cm = [self.text_width_cm / ncols] * ncols
        else:
            col_cm = [float(w) for w in widths]
            if len(col_cm) != ncols:
                raise ValueError(
                    f"Report.table: widths has {len(col_cm)} entries but the table has {ncols} columns"
                )
        total_cm = sum(col_cm)
        if total_cm > self.text_width_cm + 0.01:
            scale = self.text_width_cm / total_cm
            col_cm = [w * scale for w in col_cm]
            self.warnings.append(
                f"table caption {caption!r}: widths totalled {total_cm:.2f} cm "
                f"(> {self.text_width_cm:.2f} cm text width); scaled by {scale:.3f}"
            )

        col_tw = [max(cm_to_twips(w), 120) for w in col_cm]
        total_tw = sum(col_tw)

        align_list = list(aligns) if aligns else ["center"] * ncols
        while len(align_list) < ncols:
            align_list.append("center")
        align_list = [str(a).lower() for a in align_list[:ncols]]
        if first_col_align and ncols:
            align_list[0] = str(first_col_align).lower()

        if caption:
            self.caption(caption, keep_next=True)

        # ---- table properties -------------------------------------------
        border = '<w:{side} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        tbl_pr = (
            "<w:tblPr>"
            f'<w:tblW w:w="{total_tw}" w:type="dxa"/>'
            '<w:jc w:val="center"/>'
            "<w:tblBorders>"
            + "".join(border.format(side=s) for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
            + "</w:tblBorders>"
            '<w:tblLayout w:type="fixed"/>'
            "<w:tblCellMar>"
            '<w:top w:w="28" w:type="dxa"/><w:left w:w="85" w:type="dxa"/>'
            '<w:bottom w:w="28" w:type="dxa"/><w:right w:w="85" w:type="dxa"/>'
            "</w:tblCellMar>"
            '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
            'w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
            "</w:tblPr>"
        )
        grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in col_tw) + "</w:tblGrid>"

        def cell(text: str, idx: int, *, bold: bool, shade: str | None) -> str:
            tcpr = f'<w:tcPr><w:tcW w:w="{col_tw[idx]}" w:type="dxa"/>'
            if shade:
                tcpr += f'<w:shd w:val="clear" w:color="auto" w:fill="{_attr(shade)}"/>'
            tcpr += '<w:vAlign w:val="center"/></w:tcPr>'
            ppr = (
                "<w:pPr>"
                + self._spacing(40, 40, line=280)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                + f'<w:jc w:val="{_attr(align_list[idx])}"/>'
                + "</w:pPr>"
            )
            run = self._run(
                "" if text is None else str(text),
                font_size,
                bold=bold,
            )
            return f"<w:tc>{tcpr}<w:p>{ppr}{run}</w:p></w:tc>"

        trs: list[str] = []
        if headers is not None:
            cells = []
            for i in range(ncols):
                htxt = headers[i] if i < len(headers) else ""
                cells.append(cell(htxt, i, bold=header_bold, shade=header_shade))
            trs.append(
                "<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>"
                + "".join(cells)
                + "</w:tr>"
            )
        for row in data_rows:
            cells = []
            for i in range(ncols):
                val = row[i] if i < len(row) else ""
                cells.append(cell(val, i, bold=False, shade=None))
            trs.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>" + "".join(cells) + "</w:tr>")

        self._emit(f"<w:tbl>{tbl_pr}{grid}{''.join(trs)}</w:tbl>", "table")

    # ------------------------------------------------------------------
    # figures
    # ------------------------------------------------------------------

    def _register_image(self, path: str) -> tuple[dict, int, int]:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Report.figure: image not found: {path}")
        with open(path, "rb") as fh:
            data = fh.read()
        w_px, h_px, ext, ct = image_size(data, path)
        key = hashlib.sha1(data).hexdigest()
        if key in self._image_cache:
            return self._images[self._image_cache[key]], w_px, h_px
        idx = len(self._images) + 1
        name = f"image{idx}.{ext}"
        ent = {
            "name": name,
            "part": f"word/media/{name}",
            "data": data,
            "rid": f"rId{self._next_rid}",
            "ct": ct,
            "ext": ext,
        }
        self._next_rid += 1
        self._images.append(ent)
        self._image_cache[key] = idx - 1
        return ent, w_px, h_px

    def _drawing(self, rid: str, cx: int, cy: int, name: str, descr: str) -> str:
        did = self._next_docpr
        self._next_docpr += 1
        return (
            "<w:drawing>"
            '<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{did}" name="{_attr(name)}" descr="{_attr(descr)}"/>'
            "<wp:cNvGraphicFramePr>"
            f'<a:graphicFrameLocks xmlns:a="{A_NS}" noChangeAspect="1"/>'
            "</wp:cNvGraphicFramePr>"
            f'<a:graphic xmlns:a="{A_NS}">'
            f'<a:graphicData uri="{PIC_NS}">'
            f'<pic:pic xmlns:pic="{PIC_NS}">'
            "<pic:nvPicPr>"
            f'<pic:cNvPr id="{did}" name="{_attr(name)}" descr="{_attr(descr)}"/>'
            "<pic:cNvPicPr/>"
            "</pic:nvPicPr>"
            "<pic:blipFill>"
            f'<a:blip r:embed="{_attr(rid)}"/>'
            "<a:stretch><a:fillRect/></a:stretch>"
            "</pic:blipFill>"
            "<pic:spPr>"
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            "</pic:spPr>"
            "</pic:pic>"
            "</a:graphicData>"
            "</a:graphic>"
            "</wp:inline>"
            "</w:drawing>"
        )

    def figure(
        self,
        path: str,
        caption: str | None = None,
        width_cm: float = 14.0,
        *,
        keep_next: bool = True,
    ) -> None:
        """Insert a PNG/JPEG image, centred, with an optional caption below.

        The pixel size is read from the file header with :mod:`struct`; the
        height follows from the aspect ratio.  ``width_cm`` is clamped to the
        usable text width (15.40 cm) and a warning is recorded when clamped.
        """
        ent, w_px, h_px = self._register_image(path)
        if w_px <= 0 or h_px <= 0:
            raise ValueError(f"Report.figure: {path!r} reports a zero-sized image")

        width = float(width_cm)
        if width > self.text_width_cm:
            self.warnings.append(
                f"figure {caption or path!r}: width_cm={width:.2f} exceeds the "
                f"{self.text_width_cm:.2f} cm text width; clamped"
            )
            width = self.text_width_cm
        cx = cm_to_emu(width)
        cy = int(round(cx * h_px / w_px))

        ppr = "<w:pPr>"
        if keep_next and caption:
            ppr += "<w:keepNext/>"
        ppr += (
            self._spacing(120, 60)
            + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            + '<w:jc w:val="center"/>'
            + "</w:pPr>"
        )
        run = f"<w:r>{self._rpr()}{self._drawing(ent['rid'], cx, cy, ent['name'], caption or '')}</w:r>"
        self._emit(f"<w:p>{ppr}{run}</w:p>", "figure")

        if caption:
            self.caption(caption)
        else:
            self._last_kind = "figure"

    # ------------------------------------------------------------------
    # misc
    # ------------------------------------------------------------------

    def pagebreak(self) -> None:
        """Insert an explicit page break."""
        p = (
            "<w:p><w:pPr>"
            + self._spacing(0, 0, line=240)
            + "</w:pPr>"
            '<w:r><w:br w:type="page"/></w:r>'
            "</w:p>"
        )
        self._emit(p, "pagebreak")

    # ------------------------------------------------------------------
    # package assembly
    # ------------------------------------------------------------------

    def _content_types_xml(self) -> str:
        defaults: dict[str, str] = {
            "rels": "application/vnd.openxmlformats-package.relationships+xml",
            "xml": "application/xml",
        }
        for img in self._images:
            defaults[img["ext"]] = ACCEPTED_IMAGE_EXT.get(img["ext"], img["ct"])
        body = "".join(
            f'<Default Extension="{_attr(e)}" ContentType="{_attr(c)}"/>'
            for e, c in defaults.items()
        )
        return (
            XML_DECL
            + f'<Types xmlns="{CT_NS}">'
            + body
            + f'<Override PartName="/word/document.xml" ContentType="{CT_DOCUMENT}"/>'
            + f'<Override PartName="/word/styles.xml" ContentType="{CT_STYLES}"/>'
            + f'<Override PartName="/word/settings.xml" ContentType="{CT_SETTINGS}"/>'
            + f'<Override PartName="/word/numbering.xml" ContentType="{CT_NUMBERING}"/>'
            + f'<Override PartName="/word/footer1.xml" ContentType="{CT_FOOTER}"/>'
            + f'<Override PartName="/docProps/core.xml" ContentType="{CT_CORE}"/>'
            + f'<Override PartName="/docProps/app.xml" ContentType="{CT_APP}"/>'
            + "</Types>"
        )

    def _root_rels_xml(self) -> str:
        return (
            XML_DECL
            + f'<Relationships xmlns="{PKG_REL_NS}">'
            + f'<Relationship Id="rId1" Type="{RT_OFFICE_DOCUMENT}" Target="word/document.xml"/>'
            + f'<Relationship Id="rId2" Type="{RT_CORE_PROPS}" Target="docProps/core.xml"/>'
            + f'<Relationship Id="rId3" Type="{RT_EXT_PROPS}" Target="docProps/app.xml"/>'
            + "</Relationships>"
        )

    def _document_rels_xml(self) -> str:
        rels = [
            f'<Relationship Id="rId1" Type="{RT_STYLES}" Target="styles.xml"/>',
            f'<Relationship Id="rId2" Type="{RT_SETTINGS}" Target="settings.xml"/>',
            f'<Relationship Id="rId3" Type="{RT_NUMBERING}" Target="numbering.xml"/>',
            f'<Relationship Id="rId4" Type="{RT_FOOTER}" Target="footer1.xml"/>',
        ]
        for img in self._images:
            rels.append(
                f'<Relationship Id="{img["rid"]}" Type="{RT_IMAGE}" Target="media/{img["name"]}"/>'
            )
        return XML_DECL + f'<Relationships xmlns="{PKG_REL_NS}">' + "".join(rels) + "</Relationships>"

    def _styles_xml(self) -> str:
        a, e, he, acc = (
            _attr(self.ascii_font),
            _attr(self.east_font),
            _attr(self.heading_east_font),
            _attr(self.accent),
        )
        body_sz = int(round(self.body_size_pt * 2))
        line = int(round(self.line_spacing * 240))

        def heading_style(level: int, size_pt: float, color: str | None) -> str:
            sz = int(round(size_pt * 2))
            col = f'<w:color w:val="{_attr(color)}"/>' if color else ""
            return (
                f'<w:style w:type="paragraph" w:styleId="Heading{level}">'
                f'<w:name w:val="heading {level}"/>'
                '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                f'<w:uiPriority w:val="{10 - level}"/><w:qFormat/>'
                "<w:pPr>"
                "<w:keepNext/><w:keepLines/>"
                f'<w:spacing w:before="240" w:after="120" w:line="{line}" w:lineRule="auto"/>'
                '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                '<w:jc w:val="left"/>'
                f'<w:outlineLvl w:val="{level - 1}"/>'
                "</w:pPr>"
                "<w:rPr>"
                f'<w:rFonts w:ascii="{a}" w:hAnsi="{a}" w:eastAsia="{he}" w:cs="{a}"/>'
                "<w:b/><w:bCs/>" + col +
                f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
                "</w:rPr>"
                "</w:style>"
            )

        def toc_style(level: int) -> str:
            indent = 420 * (level - 1)
            return (
                f'<w:style w:type="paragraph" w:styleId="TOC{level}">'
                f'<w:name w:val="toc {level}"/>'
                '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                f'<w:uiPriority w:val="{39 + level}"/>'
                "<w:pPr>"
                f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W_TW}"/></w:tabs>'
                '<w:spacing w:before="60" w:after="60" w:line="280" w:lineRule="auto"/>'
                f'<w:ind w:left="{indent}" w:firstLine="0" w:firstLineChars="0"/>'
                '<w:jc w:val="left"/>'
                "</w:pPr>"
                f'<w:rPr><w:rFonts w:ascii="{a}" w:hAnsi="{a}" w:eastAsia="{e}" w:cs="{a}"/>'
                f'<w:sz w:val="{body_sz}"/><w:szCs w:val="{body_sz}"/></w:rPr>'
                "</w:style>"
            )

        return (
            XML_DECL
            + f'<w:styles xmlns:w="{W_NS}">'
            + "<w:docDefaults>"
            + "<w:rPrDefault><w:rPr>"
            + f'<w:rFonts w:ascii="{a}" w:hAnsi="{a}" w:eastAsia="{e}" w:cs="{a}"/>'
            + f'<w:sz w:val="{body_sz}"/><w:szCs w:val="{body_sz}"/>'
            + '<w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/>'
            + "</w:rPr></w:rPrDefault>"
            + "<w:pPrDefault><w:pPr>"
            + self._spacing(0, 0, line=line)
            + "</w:pPr></w:pPrDefault>"
            + "</w:docDefaults>"
            + '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            + '<w:name w:val="Normal"/><w:qFormat/>'
            + "<w:pPr>"
            + self._spacing(0, 0, line=line)
            + '<w:jc w:val="both"/></w:pPr>'
            + "<w:rPr>"
            + f'<w:rFonts w:ascii="{a}" w:hAnsi="{a}" w:eastAsia="{e}" w:cs="{a}"/>'
            + f'<w:sz w:val="{body_sz}"/><w:szCs w:val="{body_sz}"/></w:rPr>'
            + "</w:style>"
            + heading_style(1, 16.0, self.accent)
            + heading_style(2, 14.0, self.accent)
            + heading_style(3, 12.5, None)
            + toc_style(1)
            + toc_style(2)
            + toc_style(3)
            + '<w:style w:type="paragraph" w:styleId="Caption">'
            + '<w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
            + "<w:qFormat/>"
            + "<w:pPr>"
            + '<w:spacing w:before="60" w:after="60" w:line="280" w:lineRule="auto"/>'
            + '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            + '<w:jc w:val="center"/><w:outlineLvl w:val="9"/>'
            + "</w:pPr>"
            + "<w:rPr>"
            + f'<w:rFonts w:ascii="{a}" w:hAnsi="{a}" w:eastAsia="{e}" w:cs="{a}"/>'
            + '<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>'
            + "</w:style>"
            + "</w:styles>"
        )

    def _settings_xml(self) -> str:
        mf = _attr(self.math_font)
        return (
            XML_DECL
            + f'<w:settings xmlns:w="{W_NS}" xmlns:m="{M_NS}">'
            + '<w:zoom w:percent="100"/>'
            + '<w:defaultTabStop w:val="420"/>'
            + '<w:characterSpacingControl w:val="compressPunctuation"/>'
            + '<w:updateFields w:val="true"/>'
            + "<w:compat>"
            + "<w:useFELayout/>"
            + '<w:compatSetting w:name="compatibilityMode" '
            'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>'
            + "</w:compat>"
            + "<m:mathPr>"
            + f'<m:mathFont m:val="{mf}"/>'
            + '<m:brkBin m:val="before"/><m:brkBinSub m:val="--"/>'
            + '<m:smallFrac m:val="0"/><m:dispDef/>'
            + '<m:lMargin m:val="0"/><m:rMargin m:val="0"/>'
            + '<m:defJc m:val="centerGroup"/><m:wrapIndent m:val="1440"/>'
            + '<m:intLim m:val="subSup"/><m:naryLim m:val="undOvr"/>'
            + "</m:mathPr>"
            + "</w:settings>"
        )

    def _numbering_xml(self) -> str:
        def bullet_lvl(ilvl: int, char: str, font: str, left: int) -> str:
            return (
                f'<w:lvl w:ilvl="{ilvl}">'
                '<w:start w:val="1"/><w:numFmt w:val="bullet"/>'
                f'<w:lvlText w:val="{_attr(char)}"/>'
                '<w:lvlJc w:val="left"/>'
                f'<w:pPr><w:ind w:left="{left}" w:hanging="420"/></w:pPr>'
                f'<w:rPr><w:rFonts w:ascii="{_attr(font)}" w:hAnsi="{_attr(font)}" w:hint="default"/></w:rPr>'
                "</w:lvl>"
            )

        def number_lvl(ilvl: int, fmt: str, left: int) -> str:
            return (
                f'<w:lvl w:ilvl="{ilvl}">'
                '<w:start w:val="1"/>'
                f'<w:numFmt w:val="{fmt}"/>'
                f'<w:lvlText w:val="%{ilvl + 1}."/>'
                '<w:lvlJc w:val="left"/>'
                f'<w:pPr><w:ind w:left="{left}" w:hanging="420"/></w:pPr>'
                "</w:lvl>"
            )

        bullet = (
            '<w:abstractNum w:abstractNumId="0">'
            '<w:multiLevelType w:val="hybridMultilevel"/>'
            + bullet_lvl(0, "\uf0b7", "Symbol", 900)
            + bullet_lvl(1, "o", "Courier New", 1320)
            + bullet_lvl(2, "\uf0a7", "Wingdings", 1740)
            + bullet_lvl(3, "\uf0b7", "Symbol", 2160)
            + "</w:abstractNum>"
        )
        decimal = (
            '<w:abstractNum w:abstractNumId="1">'
            '<w:multiLevelType w:val="multilevel"/>'
            + number_lvl(0, "decimal", 900)
            + number_lvl(1, "lowerLetter", 1320)
            + number_lvl(2, "lowerRoman", 1740)
            + number_lvl(3, "decimal", 2160)
            + "</w:abstractNum>"
        )
        nums = [
            '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>',
            '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>',
        ]
        for nid in self._num_ids:
            nums.append(f'<w:num w:numId="{nid}"><w:abstractNumId w:val="1"/></w:num>')

        return (
            XML_DECL
            + f'<w:numbering xmlns:w="{W_NS}">'
            + bullet
            + decimal
            + "".join(nums)
            + "</w:numbering>"
        )

    def _footer_xml(self) -> str:
        rpr = self._rpr(10.5)
        return (
            XML_DECL
            + f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
            + "<w:p><w:pPr>"
            + '<w:pStyle w:val="Footer"/>'
            + self._spacing(0, 0, line=240)
            + '<w:jc w:val="center"/>'
            + f"{rpr}</w:pPr>"
            + f'<w:r>{rpr}<w:t xml:space="preserve">第 </w:t></w:r>'
            + f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
            + f'<w:r>{rpr}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            + f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
            + f'<w:r>{rpr}<w:t>1</w:t></w:r>'
            + f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>'
            + f'<w:r>{rpr}<w:t xml:space="preserve"> 页</w:t></w:r>'
            + "</w:p></w:ftr>"
        )

    def _sectpr(self) -> str:
        return (
            "<w:sectPr>"
            '<w:footerReference w:type="default" r:id="rId4"/>'
            f'<w:pgSz w:w="{A4_W_TW}" w:h="{A4_H_TW}"/>'
            f'<w:pgMar w:top="{MARGIN_TB_TW}" w:right="{MARGIN_LR_TW}" '
            f'w:bottom="{MARGIN_TB_TW}" w:left="{MARGIN_LR_TW}" '
            'w:header="851" w:footer="851" w:gutter="0"/>'
            '<w:cols w:space="425"/>'
            '<w:docGrid w:linePitch="312"/>'
            "</w:sectPr>"
        )

    def _document_xml(self) -> str:
        blocks = list(self._blocks)
        # Word is happiest when the body does not end on a table.
        if not blocks or blocks[-1].startswith("<w:tbl"):
            blocks.append(
                "<w:p><w:pPr>"
                + self._spacing(0, 0)
                + '<w:ind w:firstLine="0" w:firstLineChars="0"/></w:pPr></w:p>'
            )
        return (
            _DOCUMENT_ROOT_OPEN
            + "<w:body>"
            + "".join(blocks)
            + self._sectpr()
            + "</w:body></w:document>"
        )

    def _core_xml(self) -> str:
        return (
            XML_DECL
            + '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            + f"<dc:title>{_esc(self.title)}</dc:title>"
            + f"<dc:subject>{_esc(self.subtitle)}</dc:subject>"
            + f"<dc:creator>{_esc(self.author)}</dc:creator>"
            + f"<cp:lastModifiedBy>{_esc(self.author)}</cp:lastModifiedBy>"
            + "<cp:revision>1</cp:revision>"
            + f'<dcterms:created xsi:type="dcterms:W3CDTF">{self._created}</dcterms:created>'
            + f'<dcterms:modified xsi:type="dcterms:W3CDTF">{self._created}</dcterms:modified>'
            + "</cp:coreProperties>"
        )

    def _app_xml(self) -> str:
        return (
            XML_DECL
            + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            + "<Template>Normal.dotm</Template>"
            + "<Company></Company>"
            + "<Pages>1</Pages>"
            + "<Words>0</Words>"
            + "<Characters>0</Characters>"
            + "<Paragraphs>0</Paragraphs>"
            + "<TotalTime>0</TotalTime>"
            + "<ScaleCrop>false</ScaleCrop>"
            + "<LinksUpToDate>false</LinksUpToDate>"
            + "<CharactersWithSpaces>0</CharactersWithSpaces>"
            + "<SharedDoc>false</SharedDoc>"
            + "<HyperlinksChanged>false</HyperlinksChanged>"
            + "<Application>Microsoft Office Word</Application>"
            + "<AppVersion>16.0000</AppVersion>"
            + "<DocSecurity>0</DocSecurity>"
            + "</Properties>"
        )

    def parts(self) -> list[tuple[str, bytes | str]]:
        """Return the complete list of OPC parts ``(part_name, data)``."""
        out: list[tuple[str, bytes | str]] = [
            ("[Content_Types].xml", self._content_types_xml()),
            ("_rels/.rels", self._root_rels_xml()),
            ("docProps/core.xml", self._core_xml()),
            ("docProps/app.xml", self._app_xml()),
            ("word/document.xml", self._document_xml()),
            ("word/_rels/document.xml.rels", self._document_rels_xml()),
            ("word/styles.xml", self._styles_xml()),
            ("word/settings.xml", self._settings_xml()),
            ("word/numbering.xml", self._numbering_xml()),
            ("word/footer1.xml", self._footer_xml()),
            ("word/_rels/footer1.xml.rels", _EMPTY_RELS),
        ]
        for img in self._images:
            out.append((img["part"], img["data"]))
        return out

    def save(self, path: str) -> str:
        """Write the ``.docx`` package to ``path`` and return the absolute path."""
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in self.parts():
                zf.writestr(name, data)
        return os.path.abspath(path)


# --------------------------------------------------------------------------
# Demo:  python report_docx.py
# --------------------------------------------------------------------------


def _demo_png(path: str, width: int = 360, height: int = 220) -> None:
    """Minimal stdlib PNG encoder (zlib + struct) used by the demo only."""
    import math
    import struct as _struct
    import zlib

    raw = bytearray()
    for y in range(height):
        raw.append(0)                                  # filter type 0
        for x in range(width):
            r = int(60 + 150 * x / max(width - 1, 1))
            g = int(160 * y / max(height - 1, 1))
            b = 210
            ly = int(height * 0.5 + (height * 0.32) * math.sin(x / 22.0))
            if abs(y - ly) <= 1:
                r, g, b = 200, 30, 30
            raw += bytes((r, g, b))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            _struct.pack(">I", len(payload))
            + tag
            + payload
            + _struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    blob = b"\x89PNG\r\n\x1a\n"
    blob += chunk(b"IHDR", _struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    blob += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    blob += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)


def _main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    fig = os.path.join(here, "report_demo_fig.png")
    _demo_png(fig)

    r = Report(
        title="纯 Python 生成 Word 报告示例",
        subtitle="report_docx.Report 演示",
        author="DSH",
        date="2026年9月",
    )
    r.cover()
    r.toc()

    r.h1("1 引言")
    r.p(r"这是一个使用纯标准库生成的 Word 文档示例，行内公式如 $\alpha + \beta$ 会转换成真正的 OMML 公式。")
    r.p("这一段不缩进，并且左对齐。", first_indent=False, align="left")
    r.h2("1.1 列表")
    r.bullet("要点一")
    r.bullet("子要点", level=1)
    r.num("第一条")
    r.num("第二条")

    r.h2("1.2 公式")
    r.eq(r"\dot{V} = \frac{T\cos\alpha - D}{m} - g\sin\gamma", number="(1)")
    r.eq(r"\sum_{i=1}^{n} x_i^2 + \sqrt[3]{y} + \begin{bmatrix} a & b \\ c & d \end{bmatrix}",
         number="(2)")

    r.h3("1.2.1 表格与插图")
    r.table(
        headers=["列1", "列2"],
        rows=[["a", "b"], ["c", "d"]],
        caption="表 1-1 参数表",
        widths=[6.0, 6.0],
        font_size=10.5,
        aligns=["center", "center"],
    )
    r.figure(fig, caption="图 1-1 仿真结果", width_cm=12.0)
    r.note("注：图中曲线为演示数据。")

    out = os.path.join(here, "report_demo.docx")
    r.save(out)
    print(f"wrote {out}")
    for w in r.warnings:
        print("warning:", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

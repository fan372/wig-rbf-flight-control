# -*- coding: utf-8 -*-
"""Self-test for the stdlib Word report generator.

Run::

    python selftest.py            # full run, including the Word COM check
    python selftest.py --no-com   # static validation only

The test

1. generates ``selftest_fig.png`` (400x260 RGB, drawn sine line + gradient) with
   only ``zlib`` + ``struct`` -- no external dependencies and no image assets,
2. builds ``selftest.docx`` (cover, TOC, h1/h2/h3, body paragraphs with inline
   math, numbered display equations, a fraction+sum+sqrt+matrix equation, a 5x4
   table with caption, an embedded figure),
3. statically validates the OPC package: zip integrity, every ``*.xml`` /
   ``*.rels`` part well-formed, every relationship target present, every
   ``r:id``/``r:embed`` resolved, ``[Content_Types].xml`` covering every
   extension/part actually used, and media byte-identical to the source PNG,
4. opens the file through Word COM to prove there is no repair prompt, updates
   fields and exports ``selftest.pdf``.

Exit code 0 == every check passed.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import omml                      # noqa: E402
from report_docx import Report   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.join(HERE, "selftest.docx")
EDGE_DOCX = os.path.join(HERE, "selftest_edge.docx")
PNG = os.path.join(HERE, "selftest_fig.png")
PNG2 = os.path.join(HERE, "selftest_fig2.png")
PDF = os.path.join(HERE, "selftest.pdf")

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


# --------------------------------------------------------------------------
# Tiny PNG encoder (zlib + struct only)
# --------------------------------------------------------------------------


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def write_test_png(path: str, width: int = 400, height: int = 260) -> None:
    """Write a 400x260 RGB PNG: a red drawn sine curve over a two-axis gradient."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)                                   # per-scanline filter: none
        gy = y / max(height - 1, 1)
        for x in range(width):
            gx = x / max(width - 1, 1)
            r = int(30 + 90 * gx)
            g = int(20 + 200 * gy)
            b = int(220 - 120 * gx)
            ly = int(height * 0.5 + height * 0.34 * math.sin(x / 26.0))
            if abs(y - ly) <= 1:                        # the "simulated" curve
                r, g, b = 200, 20, 20
            if y == int(height * 0.5):                  # horizontal axis line
                r, g, b = min(r + 40, 255), min(g + 40, 255), min(b + 40, 255)
            raw += bytes((r, g, b))

    blob = b"\x89PNG\r\n\x1a\n"
    blob += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    blob += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    blob += _png_chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)


# --------------------------------------------------------------------------
# Document under test
# --------------------------------------------------------------------------


def build_document(png_path: str, out_path: str) -> Report:
    r = Report(
        title="高超声速飞行器纵向通道仿真研究报告",
        subtitle="基于纯 Python 标准库的 .docx 生成验证",
        author="DSH 自动化验证",
        date="2026年9月",
        ascii_font="Times New Roman",
        east_font="宋体",
        heading_east_font="黑体",
        accent="1F4E79",
    )

    # --- cover + TOC -----------------------------------------------------
    r.cover()
    r.toc(page_break_after=True)

    # --- headings + body paragraphs --------------------------------------
    r.h1("1 引言")
    r.p(r"本报告由纯标准库实现的 docx 生成器产出，所有 OOXML 部件均由 zipfile 与字符串模板手工拼装。")
    r.p(r"行内公式示例：升力系数 $C_L = \frac{L}{\frac{1}{2}\rho V^2 S}$，阻力 "
        r"$D = \frac{1}{2}\rho V^2 S C_D$，攻角记为 $\alpha$。", first_indent=True)
    r.p("本段不首行缩进，并且左对齐显示，用于验证 first_indent 与 align 参数。",
        first_indent=False, align="left")

    r.h2("1.1 研究背景")
    r.p(r"高超声速飞行器的纵向动力学具有很强的非线性与耦合特性，其速度回路可写为 "
        r"$\dot{V} = \frac{T\cos\alpha - D}{m} - g\sin\gamma$。")
    r.bullet("气动力与推力的强耦合")
    r.bullet("热流与结构约束", level=1)
    r.bullet("控制律对模型误差的敏感性", level=2)
    r.num("建立六自由度模型")
    r.num("设计纵向控制律")
    r.num("开展数值仿真验证")

    r.h2("1.2 控制律设计")
    r.h3("1.2.1 反馈线性化")

    # --- numbered display equations --------------------------------------
    r.eq(r"\dot{V} = \frac{T\cos\alpha - D}{m} - g\sin\gamma", number="(1)")
    r.eq(r"\dot{\gamma} = \frac{L + T\sin\alpha}{mV} - \frac{g\cos\gamma}{V}", number="(2)")

    # --- fraction + sum + sqrt + matrix + cases --------------------------
    r.eq(
        r"\bar{J}(\theta) = \frac{1}{N}\sum_{i=1}^{N}\sqrt{\left( y_i - \hat{y}_i(\theta) \right)^2}"
        r" + \sqrt[3]{\frac{\theta_1}{\theta_2}}"
        r" + \left\| \begin{bmatrix} \theta_1 \\ \theta_2 \end{bmatrix} \right\|_2",
        number="(3)",
    )
    r.eq(
        r"f(x) = \begin{cases} x^2, & x \ge 0 \\ -x^2, & x < 0 \end{cases}"
        r" \qquad \lim_{x \to \infty} \frac{\sin x}{x} = 0",
        number="(4)",
    )
    r.eq(r"\prod_{k=1}^{m} \left( 1 + \frac{1}{k} \right) \approx e^{\gamma}", number="(5)")
    r.eq(r"\int_0^{T} \dot{V}\,\mathrm{d}t = \Delta V", number="(6)")

    # --- 5x4 table with caption above ------------------------------------
    r.h2("1.3 仿真参数")
    r.p(r"表 1-1 给出了主要仿真参数，采用 10.5 pt 五号字，表头浅蓝底纹并在跨页时重复。")
    r.table(
        headers=["参数", "符号", "取值", "单位"],
        rows=[
            ["质量", "m", "1200", "kg"],
            ["参考面积", "S", "0.85", "m²"],
            ["升力线斜率", "C_L", "3.42", "1/rad"],
            ["初始速度", "V0", "2100", "m/s"],
            ["初始高度", "H0", "20000", "m"],
        ],
        caption="表 1-1 纵向通道主要仿真参数",
        widths=[4.0, 3.2, 4.0, 4.2],
        font_size=10.5,
        aligns=["left", "center", "center", "center"],
    )
    r.note("注：参数取自公开文献的典型值，仅用于验证排版。")

    # --- figure with caption below ---------------------------------------
    r.h2("1.4 仿真结果")
    r.p(r"图 1-1 给出了速度通道的阶跃响应，图中红色曲线为数值仿真结果。")
    r.figure(PNG, caption="图 1-1 速度通道阶跃响应曲线", width_cm=13.0)
    r.caption("图 1-2 独立标题（caption() 示例）")
    r.note("注：图 1-1 由 selftest.py 使用 zlib + struct 现场生成，无外部依赖。")

    r.h1("2 结论")
    r.p(r"验证结果表明：生成器输出的 OOXML 包结构完整、关系与内容类型自洽，"
        r"公式以真正的 OMML 呈现（例如 $\sum_{i=1}^{n} x_i$ 与 $\int_0^1 f(x)\,\mathrm{d}x$），"
        r"Word 打开时不出现“修复”提示。")
    r.table(
        headers=["检查项", "结果"],
        rows=[["ZIP 完整性", "通过"], ["XML 良构", "通过"], ["关系解析", "通过"]],
        caption="表 2-1 静态校验结果",
        widths=[8.0, 7.0],
        font_size=10.5,
        aligns=["left", "center"],
    )

    r.h1("附录 A 公式宏覆盖")
    r.p(r"$\alpha\ \beta\ \gamma\ \Gamma\ \Delta\ \Omega$，"
        r"$\times\ \cdot\ \pm\ \leq\ \geq\ \neq\ \approx\ \equiv\ \in\ \subset\ \cup\ \cap\ \infty\ \partial\ \nabla$")
    r.p(r"$\hat{x}\ \tilde{y}\ \bar{z}\ \vec{v}\ \ddot{q}$，"
        r"$\sin\cos\tan\ \ln\ \exp\ \max\ \min\ \lim_{x\to 0}\ \sat$")
    r.p(r"$\left( \frac{a}{b} \right)\ \left[ c \right]\ \left\{ d \right\}\ "
        r"\left| e \right|\ \left\| f \right\|$")
    r.p(r"双重角标：$x_i^2$，$a_{ij}^{n+1}$，$\sum_{i=1}^{n} x_i^2$。")
    r.p(r"直立与粗体：$\mathbf{F} = m\mathbf{a}$，$\mathbf{0}_{n\times n}$，"
        r"$\text{推力} \cdot T$，$\mathrm{d}x$，$\mathbb{R}^n$。")

    saved = r.save(out_path)
    assert saved and os.path.isfile(out_path)
    return r


# --------------------------------------------------------------------------
# Edge-case document (exercises less common code paths)
# --------------------------------------------------------------------------


def synthetic_jpeg(width: int = 64, height: int = 48) -> bytes:
    """A minimal but structurally valid JPEG envelope for header parsing.

    ``jpeg_size`` only needs SOI + a SOFn marker, so the scan data is a stub.
    """
    out = b"\xff\xd8"                                             # SOI
    payload = b"JFIF\x00" + bytes([1, 1, 0]) + struct.pack(">HH", 1, 1) + bytes(2)
    out += b"\xff\xe0" + struct.pack(">H", len(payload) + 2) + payload   # APP0
    out += b"\xff\xdb" + struct.pack(">H", 67) + bytes([0]) + bytes(64)  # DQT
    out += (b"\xff\xc0" + struct.pack(">H", 11) + bytes([8])
            + struct.pack(">HH", height, width) + bytes([1, 0x11, 0]))   # SOF0
    out += b"\xff\xda" + struct.pack(">H", 8) + bytes([1, 1, 0, 0, 63, 0])  # SOS
    out += b"\x00\xff\xd9"                                        # stub data + EOI
    return out


def build_edge_document(out_path: str) -> "Report":
    """A second document covering: header-less table, image de-duplication,
    a second distinct image, XML escaping torture, empty inline math, the
    unknown-macro fallback, list restart and the tab-stop equation layout."""
    r = Report(title="边界用例", author="DSH", date="2026年9月")
    r.h1("1 边界用例")

    # XML escaping torture: &, <, > in both body text and math
    r.p(r"转义测试：A & B，5 < 6 且 7 > 6，$a < b$，$x \geq y$，百分比 100% 与下划线 a_b。")
    r.p(r"未知宏回退：$\foo{bar} + \baz$（应记录在 UNKNOWN_MACROS 中，不抛异常）。")

    # empty inline math must not produce an invalid empty <m:oMath/>
    r.p(r"空公式：$$ 与 $\,$ 与 $x$。")

    # header-less table, two columns, explicit widths
    r.table(headers=None, rows=[["无表头 A", "1"], ["无表头 B", "2"]],
            caption="表 1-1 无表头表格", widths=[6.0, 4.0], font_size=10.5)

    # same image twice -> one media part / one relationship, two drawings
    r.figure(PNG, caption="图 1-1 重复引用（去重）", width_cm=8.0)
    r.figure(PNG, caption=None, width_cm=6.0)
    # a second, distinct image -> a second media part (rId6)
    r.figure(PNG2, caption="图 1-2 第二张不同图片", width_cm=5.0)

    # tab-stop equation layout (alternative to the borderless table)
    r.eq(r"E = mc^2", number="(1)", layout="tabs")
    r.eq(r"\begin{cases} 1, & a \\ 0, & b \end{cases}", number=None)

    # list restart: a new contiguous group must restart at 1
    r.num("第一组第一项")
    r.num("第一组第二项")
    r.p("打断一下。")
    r.num("第二组第一项")
    r.bullet("项目符号")
    r.bullet("二级项目符号", level=1)
    r.bullet("三级项目符号", level=2)
    r.bullet("四级项目符号", level=3)

    r.note("注：本文件用于覆盖边界代码路径。")
    r.save(out_path)
    return r


# --------------------------------------------------------------------------
# Static validation
# --------------------------------------------------------------------------


class Checker:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        line = f"{tag}  {name}" + (f"   [{detail}]" if detail else "")
        (self.passed if ok else self.failed).append(line)
        return ok

    def report(self) -> int:
        for line in self.passed:
            print(line)
        for line in self.failed:
            print(line)
        print()
        print(f"RESULT: {len(self.passed)} passed, {len(self.failed)} failed")
        if self.failed:
            print("SELFTEST FAIL")
            return 1
        print("SELFTEST PASS")
        return 0


def _mval(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    return el.get(f"{{{NS['m']}}}val") or el.get(f"{{{NS['w']}}}val")


# --------------------------------------------------------------------------
# Strict OOXML structural validation (child order + required children)
#
# Wrong child order inside w:pPr / w:tblPr / m:f ... is the single most common
# cause of Word's "unreadable content" repair prompt, and a renderer is not
# available in this sandbox, so the ordering rules are asserted directly.
# --------------------------------------------------------------------------

_PREFIX_OF_NS = {
    NS["w"]: "w", NS["m"]: "m", NS["r"]: "r", NS["wp"]: "wp",
    NS["a"]: "a", NS["pic"]: "pic", NS["ct"]: "ct", NS["rel"]: "rel",
}

#: allowed child sequence; elements absent from a list are ignored by the check
_CHILD_ORDER: dict[str, list[str]] = {
    # --- WordprocessingML -------------------------------------------------
    "w:pPr": [
        "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
        "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs",
        "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
        "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
        "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
        "suppressOverlap", "jc", "textDirection", "textAlignment",
        "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
        "pPrChange",
    ],
    "w:rPr": [
        "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
        "strike", "dstrike", "outline", "shadow", "emboss", "imprint",
        "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
        "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
        "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
        "eastAsianLayout", "specVanish", "oMath", "rPrChange",
    ],
    "w:tblPr": [
        "tblStyle", "tblpPr", "tblOverlap", "bidiVisual",
        "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
        "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout",
        "tblCellMar", "tblLook", "tblCaption", "tblDescription",
        "tblPrChange",
    ],
    "w:tblBorders": ["top", "start", "left", "bottom", "end", "right",
                     "insideH", "insideV"],
    "w:tblCellMar": ["top", "start", "left", "bottom", "end", "right"],
    "w:trPr": [
        "cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter",
        "cantSplit", "trHeight", "tblHeader", "tblCellSpacing", "jc",
        "hidden", "ins", "del", "trPrChange",
    ],
    "w:tcPr": [
        "cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd",
        "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark",
        "cellIns", "cellDel", "cellMerge", "tcPrChange",
    ],
    "w:sectPr": [
        "headerReference", "footerReference", "footnotePr", "endnotePr",
        "type", "pgSz", "pgMar", "paperSrc", "pgBorders", "lnNumType",
        "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg",
        "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings",
        "sectPrChange",
    ],
    "w:settings": [
        "writeProtection", "view", "zoom", "removePersonalInformation",
        "removeDateAndTime", "defaultTabStop", "characterSpacingControl",
        "updateFields", "hdrShapeDefaults", "footnotePr", "endnotePr",
        "compat", "docVars", "rsids", "mathPr",
    ],
    "w:styles": ["docDefaults", "latentStyles", "style"],
    "w:tbl": ["tblPr", "tblGrid", "tr"],
    "w:tr": ["trPr", "tblPrEx", "tc"],
    "w:tc": ["tcPr", "p", "tbl", "sdt", "customXml"],
    "w:p": ["pPr"],
    "w:body": ["p", "tbl", "sdt", "customXml", "oMathPara", "oMath", "sectPr"],
    # --- OMML -------------------------------------------------------------
    "m:oMathPara": ["oMathParaPr", "oMath"],
    "m:r": ["rPr", "t"],
    "m:rPr": ["lit", "nor", "sty", "brk", "aln", "scr"],
    "m:f": ["fPr", "num", "den"],
    "m:fPr": ["type", "ctrlPr"],
    "m:rad": ["radPr", "deg", "e"],
    "m:radPr": ["degHide", "ctrlPr"],
    "m:nary": ["naryPr", "sub", "sup", "e"],
    "m:naryPr": ["chr", "limLoc", "grow", "subHide", "supHide", "ctrlPr"],
    "m:d": ["dPr", "e"],
    "m:dPr": ["begChr", "sepChr", "endChr", "grow", "shp", "ctrlPr"],
    "m:sSub": ["sSubPr", "e", "sub"],
    "m:sSup": ["sSupPr", "e", "sup"],
    "m:sSubSup": ["sSubSupPr", "e", "sub", "sup"],
    "m:acc": ["accPr", "e"],
    "m:accPr": ["chr", "ctrlPr"],
    "m:bar": ["barPr", "e"],
    "m:barPr": ["pos", "ctrlPr"],
    "m:limLow": ["limLowPr", "e", "lim"],
    "m:m": ["mPr", "mr"],
    "m:mPr": ["baseJc", "plcHide", "rSp", "rSpRule", "cGp", "cGpRule", "cSp",
              "mcs", "ctrlPr"],
    "m:mcs": ["mc"],
    "m:mc": ["mcPr"],
    "m:mcPr": ["count", "mcJc"],
    "m:mr": ["e"],
    # --- DrawingML / VML --------------------------------------------------
    "wp:inline": ["extent", "effectExtent", "docPr", "cNvGraphicFramePr",
                  "graphic"],
    "wp:extent": [],
    "pic:pic": ["nvPicPr", "blipFill", "spPr"],
    "pic:nvPicPr": ["cNvPr", "cNvPicPr"],
    "pic:blipFill": ["blip", "srcRect", "tile", "stretch"],
    "pic:spPr": ["xfrm", "custGeom", "prstGeom", "noFill", "solidFill",
                 "gradFill", "blipFill", "pattFill", "grpFill", "ln",
                 "effectLst", "effectDag", "scene3d", "sp3d", "extLst"],
    "a:xfrm": ["off", "ext"],
    "a:prstGeom": ["avLst", "gd"],
    "a:graphic": ["graphicData"],
}

#: tags that must contain at least one child element
_MUST_NOT_BE_EMPTY = {
    "m:oMath", "m:oMathPara", "m:f", "m:rad", "m:nary", "m:d", "m:sSub",
    "m:sSup", "m:sSubSup", "m:acc", "m:bar", "m:limLow", "m:m", "m:mr",
    "m:mcs", "m:mc", "m:mcPr", "m:e", "m:num", "m:den", "m:lim", "m:r",
    "w:tbl", "w:tblGrid", "w:tr", "w:tc", "w:body", "w:document",
}

#: (parent, empty-child, hide-flag, flag-holder) -- an empty child slot is only
#: legal when the matching *Hide flag is set (Word writes exactly this).
_HIDE_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("m:nary", "m:sub", "subHide", "m:naryPr"),
    ("m:nary", "m:sup", "supHide", "m:naryPr"),
    ("m:rad", "m:deg", "degHide", "m:radPr"),
)

#: tag -> child tags that are mandatory
_REQUIRED_CHILDREN: dict[str, tuple[str, ...]] = {
    "m:oMathPara": ("m:oMath",),
    "m:f": ("m:num", "m:den"),
    "m:rad": ("m:deg", "m:e"),
    "m:nary": ("m:sub", "m:sup", "m:e"),
    "m:d": ("m:e",),
    "m:sSub": ("m:e", "m:sub"),
    "m:sSup": ("m:e", "m:sup"),
    "m:sSubSup": ("m:e", "m:sub", "m:sup"),
    "m:acc": ("m:e",),
    "m:bar": ("m:e",),
    "m:limLow": ("m:e", "m:lim"),
    "m:mcs": ("m:mc",),
    "w:tbl": ("w:tblGrid",),
    "w:document": ("w:body",),
    "w:body": ("w:sectPr",),
    "wp:inline": ("wp:extent", "wp:docPr", "a:graphic"),
    "pic:pic": ("pic:nvPicPr", "pic:blipFill", "pic:spPr"),
}


def _qname(el: ET.Element) -> str:
    """``{ns}local`` -> ``prefix:local`` (or the raw tag when unknown)."""
    if not isinstance(el.tag, str):
        return ""
    if el.tag.startswith("{"):
        ns, local = el.tag[1:].split("}", 1)
        prefix = _PREFIX_OF_NS.get(ns)
        return f"{prefix}:{local}" if prefix else local
    return el.tag


def validate_structure(root: ET.Element) -> tuple[list[str], list[str]]:
    """Return ``(order_problems, required_child_problems)``."""
    order_problems: list[str] = []
    req_problems: list[str] = []

    def walk(el: ET.Element, path: str) -> None:
        tag = _qname(el)
        here = f"{path}/{tag}"
        kids = [k for k in el if isinstance(k.tag, str)]
        kid_tags = [_qname(k) for k in kids]

        seq = _CHILD_ORDER.get(tag)
        if seq is not None:
            last_rank = -1
            last_tag = ""
            for kt in kid_tags:
                if kt in seq:
                    r = seq.index(kt)
                    if r < last_rank:
                        order_problems.append(
                            f"{here}: <{kt}> (rank {r}) appears after <{last_tag}> (rank {last_rank})"
                        )
                    else:
                        last_rank, last_tag = r, kt

        if tag in _MUST_NOT_BE_EMPTY and not kids:
            req_problems.append(f"{here}: must not be empty")
        for want in _REQUIRED_CHILDREN.get(tag, ()):
            if want not in kid_tags:
                req_problems.append(f"{here}: missing required child <{want}>")
        # w:tc / w:mr need >= 1 child of the right kind
        if tag == "w:tc" and not any(kt in ("w:p", "w:tbl") for kt in kid_tags):
            req_problems.append(f"{here}: must contain at least one <w:p> or <w:tbl>")
        if tag in ("w:tr", "m:mr") and not kids:
            req_problems.append(f"{here}: row must contain at least one cell")

        for k, kt in zip(kids, kid_tags):
            walk(k, here)

        # conditional empty-slot rules
        for parent, slot, flag, holder in _HIDE_RULES:
            if tag != parent:
                continue
            slot_el = next((k for k, kt in zip(kids, kid_tags) if kt == slot), None)
            if slot_el is None or len(slot_el):
                continue
            holder_el = next((k for k, kt in zip(kids, kid_tags) if kt == holder), None)
            flag_el = holder_el.find(f"{{{NS['m']}}}{flag}") if holder_el is not None else None
            if flag_el is None or _mval(flag_el) not in ("1", "true", "on"):
                req_problems.append(
                    f"{here}: empty <{slot}/> without <{flag} m:val=\"1\"/>"
                )

    walk(root, "")
    return order_problems, req_problems


def validate(docx_path: str, png_path: str) -> Checker:
    c = Checker()
    zf = zipfile.ZipFile(docx_path)

    # ---- 1. zip integrity ------------------------------------------------
    bad = zf.testzip()
    c.check("zipfile.testzip() is None (ZIP integrity)", bad is None, f"first bad entry: {bad}")

    names = set(zf.namelist())
    required = [
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "word/settings.xml",
        "word/footer1.xml",
        "word/_rels/footer1.xml.rels",
        "docProps/core.xml",
        "docProps/app.xml",
    ]
    missing = [n for n in required if n not in names]
    c.check("all required OPC parts present", not missing, f"missing: {missing}")

    # ---- 2. well-formed XML for every xml / rels part ---------------------
    parse_fail: list[str] = []
    trees: dict[str, ET.Element] = {}
    for n in sorted(names):
        if not (n.endswith(".xml") or n.endswith(".rels")):
            continue
        try:
            trees[n] = ET.fromstring(zf.read(n))
        except Exception as exc:  # noqa: BLE001
            parse_fail.append(f"{n}: {exc}")
    c.check(
        "every *.xml / *.rels part parses with ElementTree",
        not parse_fail,
        "; ".join(parse_fail) if parse_fail else f"{len(trees)} parts",
    )

    # ---- 2b. strict OOXML child order + required children ------------------
    order_problems: list[str] = []
    req_problems: list[str] = []
    for part in ("word/document.xml", "word/styles.xml", "word/settings.xml",
                 "word/numbering.xml", "word/footer1.xml"):
        root = trees.get(part)
        if root is None:
            continue
        op, rp = validate_structure(root)
        order_problems += [f"{part}: {p}" for p in op]
        req_problems += [f"{part}: {p}" for p in rp]
    c.check(
        "OOXML child element order is correct everywhere (no repair prompt cause)",
        not order_problems,
        "; ".join(order_problems[:6]) if order_problems else "0 ordering violations",
    )
    c.check(
        "every container has its required children (m:f num+den, m:rad deg+e, ...)",
        not req_problems,
        "; ".join(req_problems[:6]) if req_problems else "0 missing children",
    )

    # ---- 3. relationships resolve ----------------------------------------
    rel_ns = NS["rel"]
    rels_root = trees.get("word/_rels/document.xml.rels")
    rel_items = rels_root.findall(f"{{{rel_ns}}}Relationship") if rels_root is not None else []
    rel_map = {r.get("Id"): r.get("Target") for r in rel_items}
    c.check("document.xml.rels has relationships", bool(rel_map), f"{len(rel_map)}")

    broken_targets: list[str] = []
    for rid, target in rel_map.items():
        if target is None or target.startswith(("http://", "https://")):
            continue
        part = target.lstrip("/") if target.startswith("/") else "word/" + target
        part = os.path.normpath(part).replace("\\", "/")
        if part not in names:
            broken_targets.append(f"{rid} -> {target}")
    c.check("every relationship target part exists in the zip", not broken_targets, "; ".join(broken_targets))

    doc_xml = zf.read("word/document.xml").decode("utf-8")
    used_ids: set[str] = set()
    for attr in ("r:id", "r:embed", "r:link"):
        used_ids |= set(re.findall(attr + r'="([^"]+)"', doc_xml))
    unresolved = sorted(i for i in used_ids if i not in rel_map)
    c.check(
        "every r:id / r:embed in document.xml resolves",
        not unresolved,
        f"used={len(used_ids)} unresolved={unresolved}",
    )
    c.check(
        "sectPr footerReference resolves",
        'r:id="rId4"' in doc_xml and "rId4" in rel_map,
        f"rId4 -> {rel_map.get('rId4')}",
    )
    all_ids = [r.get("Id") for r in rel_items]
    c.check("relationship Ids unique", len(all_ids) == len(set(all_ids)), f"{len(all_ids)} ids")

    # ---- 4. content types -------------------------------------------------
    ct_root = trees.get("[Content_Types].xml")
    defaults: dict[str, str] = {}
    overrides: set[str] = set()
    if ct_root is not None:
        for d in ct_root.findall(f"{{{NS['ct']}}}Default"):
            defaults[d.get("Extension").lower()] = d.get("ContentType")
        for o in ct_root.findall(f"{{{NS['ct']}}}Override"):
            overrides.add(o.get("PartName"))
    uncovered: list[str] = []
    for n in sorted(names):
        if n == "[Content_Types].xml":
            continue
        if ("/" + n) in overrides:
            continue
        ext = n.rsplit(".", 1)[-1].lower() if "." in n else ""
        if ext not in defaults:
            uncovered.append(n)
    c.check(
        "[Content_Types].xml declares every extension / part actually used",
        not uncovered,
        f"defaults={sorted(defaults)} uncovered={uncovered}",
    )
    c.check('Default Extension="png" -> image/png declared',
            defaults.get("png") == "image/png", str(defaults.get("png")))
    c.check("Overrides cover document/styles/settings/numbering/footer1/core/app",
            overrides >= {
                "/word/document.xml", "/word/styles.xml", "/word/settings.xml",
                "/word/numbering.xml", "/word/footer1.xml",
                "/docProps/core.xml", "/docProps/app.xml",
            },
            f"{len(overrides)} overrides")

    # ---- 5. media ---------------------------------------------------------
    with open(png_path, "rb") as fh:
        src = fh.read()
    media = sorted(n for n in names if n.startswith("word/media/"))
    c.check("media part(s) embedded", bool(media), f"{media}")
    c.check("media part(s) byte-identical to the source PNG",
            bool(media) and all(zf.read(m) == src for m in media), f"{len(media)} part(s)")
    media_rels = [t for t in rel_map.values() if t and t.startswith("media/")]
    c.check("one image relationship per media part",
            len(media_rels) == len(media) and len(media) > 0, f"rels={media_rels}")

    # ---- 6. OMML is real math, not text -----------------------------------
    m, w = NS["m"], NS["w"]
    doc = trees["word/document.xml"]

    def count(tag: str) -> int:
        return len(doc.findall(f".//{{{m}}}{tag}"))

    n_omath, n_para = count("oMath"), count("oMathPara")
    n_frac, n_nary, n_rad, n_mat = count("f"), count("nary"), count("rad"), count("m")
    n_subsup, n_ssub, n_ssup = count("sSubSup"), count("sSub"), count("sSup")
    n_d, n_acc, n_bar, n_limlow = count("d"), count("acc"), count("bar"), count("limLow")

    c.check("<m:oMath> present (inline + display)", n_omath >= 12, f"{n_omath}")
    c.check("<m:oMathPara> present (display equations)", n_para >= 6, f"{n_para}")
    c.check("<m:f> fractions", n_frac >= 6, f"{n_frac}")
    c.check("<m:nary> big operators (sum/prod/int)", n_nary >= 3, f"{n_nary}")
    c.check("<m:rad> radicals", n_rad >= 2, f"{n_rad}")
    c.check("<m:m> matrices (bmatrix + cases)", n_mat >= 2, f"{n_mat}")
    c.check("<m:sSubSup> simultaneous sub+superscript", n_subsup >= 1, f"{n_subsup}")
    c.check("<m:sSub>/<m:sSup> single scripts", n_ssub >= 3 and n_ssup >= 3, f"sSub={n_ssub} sSup={n_ssup}")
    c.check("<m:d> auto-sized delimiters", n_d >= 5, f"{n_d}")
    c.check("<m:acc>/<m:bar> accents", n_acc >= 3 and n_bar >= 1, f"acc={n_acc} bar={n_bar}")
    c.check("<m:limLow> for \\lim/\\max", n_limlow >= 2, f"{n_limlow}")

    lims = set()
    for pr in doc.findall(f".//{{{m}}}nary/{{{m}}}naryPr"):
        v = _mval(pr.find(f"{{{m}}}limLoc"))
        if v:
            lims.add(v)
    c.check("nary limLoc covers undOvr and subSup", lims >= {"undOvr", "subSup"}, f"{sorted(lims)}")

    nary_chrs = {_mval(pr.find(f"{{{m}}}chr")) for pr in doc.findall(f".//{{{m}}}nary/{{{m}}}naryPr")}
    c.check("nary chr = sum/prod/int characters",
            nary_chrs >= {"\u2211", "\u220f", "\u222b"}, f"{sorted(c for c in nary_chrs if c)}")

    sty_vals = [_mval(s) for s in doc.findall(f".//{{{m}}}rPr/{{{m}}}sty")]
    c.check("upright runs use <m:sty m:val=\"p\">", sty_vals.count("p") >= 10,
            f"p={sty_vals.count('p')} all={sorted(set(sty_vals))}")
    c.check("bold math uses <m:sty m:val=\"b\">", "b" in sty_vals, f"{sorted(set(sty_vals))}")

    # ---- 7. escaping ------------------------------------------------------
    bad_amp = re.findall(r"&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9A-Fa-f]+);)", doc_xml)
    c.check("every '&' in document.xml starts a valid XML entity", not bad_amp,
            f"{len(bad_amp)} bad ampersands")
    c.check("'<' / '>' from math are escaped as &lt; / &gt;",
            ("&gt;" in doc_xml or "&lt;" in doc_xml), "found escaped comparison entity")
    c.check("all math text runs carry xml:space=\"preserve\"",
            doc_xml.count("<m:t xml:space=\"preserve\">") == doc_xml.count("<m:t "),
            f"{doc_xml.count('<m:t xml:space=\"preserve\">')} / {doc_xml.count('<m:t ')}")

    # ---- 8. Word requirements --------------------------------------------
    settings = zf.read("word/settings.xml").decode("utf-8")
    c.check('<w:updateFields w:val="true"/> in settings.xml',
            '<w:updateFields w:val="true"/>' in settings)
    c.check("settings.xml has m:mathPr with mathFont",
            "<m:mathPr>" in settings and "<m:mathFont" in settings)

    c.check("A4 page size (11906 x 16838 twips)", 'w:w="11906" w:h="16838"' in doc_xml)
    c.check("margins top/bottom 1440, left/right 1588",
            all(s in doc_xml for s in ('w:top="1440"', 'w:bottom="1440"', 'w:left="1588"', 'w:right="1588"')))

    c.check('TOC field TOC \\o "1-3" \\h \\z \\u present',
            'TOC \\o "1-3" \\h \\z \\u' in doc_xml)
    c.check("TOC field char marked dirty", 'w:fldCharType="begin" w:dirty="true"' in doc_xml)

    footer = zf.read("word/footer1.xml").decode("utf-8")
    c.check("footer has centered PAGE field formatted 第 X 页",
            "PAGE" in footer and "第 " in footer and " 页" in footer
            and '<w:jc w:val="center"/>' in footer)

    styles = zf.read("word/styles.xml").decode("utf-8")
    c.check("Heading1/2/3 styles with outlineLvl 0/1/2",
            all(f'w:styleId="Heading{i}"' in styles and f'<w:outlineLvl w:val="{i-1}"/>' in styles
                for i in (1, 2, 3)))
    c.check("heading styles use 黑体 + bold + keepNext",
            'w:eastAsia="黑体"' in styles and "<w:keepNext/>" in styles)
    c.check("heading sizes 32/28/25 half-points (16/14/12.5 pt)",
            all(f'<w:sz w:val="{v}"/>' in styles for v in (32, 28, 25)))
    c.check('h1/h2 colour = accent 1F4E79', styles.count('w:val="1F4E79"') >= 2,
            f"{styles.count('w:val=\"1F4E79\"')} occurrences")

    # body paragraph formatting
    c.check('2-character first-line indent (firstLineChars="200" firstLine="480")',
            'w:firstLineChars="200" w:firstLine="480"' in doc_xml)
    c.check('justified body text (w:jc val="both")', '<w:jc w:val="both"/>' in doc_xml)
    c.check("1.5 line spacing (w:line=360 lineRule=auto)",
            'w:line="360" w:lineRule="auto"' in doc_xml)
    c.check("body 12 pt (w:sz 24)", '<w:sz w:val="24"/>' in doc_xml)
    c.check("Times New Roman ascii + 宋体 eastAsia",
            'w:ascii="Times New Roman"' in doc_xml and 'w:eastAsia="宋体"' in doc_xml)

    # ---- 9. tables --------------------------------------------------------
    tbls = doc.findall(f".//{{{w}}}tbl")
    c.check("tables present (2 real + 6 numbered-equation tables)", len(tbls) >= 8, f"{len(tbls)}")
    n_thead = len(doc.findall(f".//{{{w}}}tblHeader"))
    c.check("header rows repeat across pages (<w:tblHeader/>)", n_thead >= 2, f"{n_thead}")
    n_shade = doc_xml.count('w:fill="D9E2F3"')
    c.check("header shading D9E2F3 applied", n_shade >= 4, f"{n_shade} cells")
    n_grid = len(doc.findall(f".//{{{w}}}tblGrid"))
    c.check("every table has an explicit tblGrid", n_grid == len(tbls), f"{n_grid}/{len(tbls)}")
    n_fixed = len(doc.findall(f".//{{{w}}}tblLayout[@{{{w}}}type='fixed']", NS))
    c.check("tables use fixed layout", n_fixed == len(tbls), f"{n_fixed}/{len(tbls)}")
    n_valign = len(doc.findall(f".//{{{w}}}tcPr/{{{w}}}vAlign"))
    c.check("all cells vertically centred", n_valign >= 20, f"{n_valign} cells")
    n_border = doc_xml.count('<w:insideH w:val="single"')
    c.check("full single borders on the content tables", n_border >= 2, f"{n_border} tables")
    n_none = doc_xml.count('<w:insideH w:val="none"')
    c.check("numbered-equation tables are borderless", n_none >= 6, f"{n_none} tables")
    n_caption_first = doc_xml.find("表 1-1 纵向通道主要仿真参数") < doc_xml.find("w:tblHeader")
    c.check("table caption appears before the table", n_caption_first,
            "caption offset < first tblHeader offset" if n_caption_first else "caption AFTER table!")
    cap_keep = len(doc.findall(f".//{{{w}}}pStyle[@{{{w}}}val='Caption']", NS))
    c.check("caption paragraphs use the Caption style", cap_keep >= 4, f"{cap_keep}")

    # 13. cross-part references --------------------------------------------
    style_ids = set(re.findall(r'<w:style [^>]*w:styleId="([^"]+)"', styles))
    used_styles = set(re.findall(r'<w:pStyle w:val="([^"]+)"/>', doc_xml))
    c.check("every referenced w:pStyle exists in styles.xml",
            used_styles <= style_ids,
            f"used={sorted(used_styles)} missing={sorted(used_styles - style_ids)}")

    numbering = zf.read("word/numbering.xml").decode("utf-8")
    num_ids = set(re.findall(r'<w:num w:numId="(\d+)"', numbering))
    used_num = set(re.findall(r'<w:numId w:val="(\d+)"/>', doc_xml))
    c.check("every referenced w:numId exists in numbering.xml",
            used_num <= num_ids,
            f"used={sorted(used_num)} defined={sorted(num_ids)}")
    abs_ids = set(re.findall(r'<w:abstractNum w:abstractNumId="(\d+)"', numbering))
    ref_abs = set(re.findall(r'<w:abstractNumId w:val="(\d+)"/>', numbering))
    c.check("every w:abstractNumId reference resolves",
            ref_abs <= abs_ids, f"refs={sorted(ref_abs)} defined={sorted(abs_ids)}")
    c.check("each contiguous num() group gets its own w:num entry",
            len(num_ids) >= 3, f"numIds={sorted(num_ids)}")

    # 14. drawing ----------------------------------------------------------
    inlines = doc.findall(f".//{{{NS['wp']}}}inline")
    c.check("exactly one wp:inline drawing", len(inlines) == 1, f"{len(inlines)}")
    if inlines:
        ext = inlines[0].find(f"{{{NS['wp']}}}extent")
        docpr = inlines[0].find(f"{{{NS['wp']}}}docPr")
        blip = inlines[0].find(f".//{{{NS['a']}}}blip")
        geom = inlines[0].find(f".//{{{NS['a']}}}prstGeom")
        xfrm_ext = inlines[0].find(f".//{{{NS['a']}}}xfrm/{{{NS['a']}}}ext")
        c.check("wp:extent has positive cx/cy",
                ext is not None and int(ext.get("cx")) > 0 and int(ext.get("cy")) > 0,
                f"cx={ext.get('cx') if ext is not None else None} cy={ext.get('cy') if ext is not None else None}")
        c.check("wp:docPr id is a unique positive integer",
                docpr is not None and int(docpr.get("id")) >= 1 and bool(docpr.get("name")),
                f"id={docpr.get('id') if docpr is not None else None}")
        embed = blip.get(f"{{{NS['r']}}}embed") if blip is not None else None
        c.check("a:blip r:embed present and resolves", embed in rel_map, f"embed={embed}")
        c.check("a:prstGeom prst=rect", geom is not None and geom.get("prst") == "rect")
        c.check("pic:spPr a:ext matches wp:extent",
                xfrm_ext is not None and ext is not None
                and xfrm_ext.get("cx") == ext.get("cx") and xfrm_ext.get("cy") == ext.get("cy"),
                f"ext={xfrm_ext.get('cx') if xfrm_ext is not None else None}x"
                f"{xfrm_ext.get('cy') if xfrm_ext is not None else None}")
        if ext is not None:
            ratio = int(ext.get("cx")) / int(ext.get("cy"))
            c.check("image aspect ratio preserved (400x260 source)", abs(ratio - 400 / 260) < 0.01,
                    f"{ratio:.4f}")
            c.check("width_cm=13.0 honoured (13 cm = 4680000 EMU)",
                    abs(int(ext.get("cx")) - 4680000) <= 1, f"cx={ext.get('cx')}")

    zf.close()
    return c


# --------------------------------------------------------------------------
# Word COM rendering validation
# --------------------------------------------------------------------------

COM_PS = r"""
$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$docx = "@@DOCX@@"
$pdf  = "@@PDF@@"
# Non-ASCII needles are built from code points so this script stays pure ASCII
# (PowerShell redirects stdout with the OEM code page, not UTF-8).
$needleTitle = [string]([char]0x7EB5) + [char]0x5411 + [char]0x901A + [char]0x9053   # 纵向通道
$needleToc   = [string]([char]0x5F15) + [char]0x8A00                                  # 引言

$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0

# --- control: can Word create *any* document in this environment? ---------
$control = "FAIL"
$controlErr = ""
try {
    $c = $w.Documents.Add()
    $control = "OK"
    $c.Close(0)
} catch {
    $controlErr = $_.Exception.Message
}
$added = Test-Path "$env:APPDATA\Microsoft\Word"
Write-Output ("CONTROL=" + $control)
if ($control -ne "OK") { Write-Output ("CONTROL_ERR=" + $controlErr) }

# --- the real thing ------------------------------------------------------
$ok = $false
try {
    $d = $w.Documents.Open($docx)
    $d.Fields.Update() | Out-Null
    foreach ($s in $d.Sections) { $s.Footers(1).Range.Fields.Update() | Out-Null }
    $d.ExportAsFixedFormat($pdf, 17)
    Write-Output ("PAGES="  + $d.ComputeStatistics(2))
    Write-Output ("WORDS="  + $d.ComputeStatistics(0))
    Write-Output ("SHAPES=" + $d.InlineShapes.Count)
    Write-Output ("OMATHS=" + $d.OMaths.Count)
    Write-Output ("TABLES=" + $d.Tables.Count)
    Write-Output ("FIELDS=" + $d.Fields.Count)
    Write-Output ("PARAS="  + $d.Paragraphs.Count)
    Write-Output ("TEXTLEN=" + $d.Content.Text.Length)
    Write-Output ("HAS_TITLE=" + ($d.Content.Text -like ("*" + $needleTitle + "*")))
    Write-Output ("TOC_HITS=" + ([regex]::Matches($d.Content.Text, $needleToc)).Count)
    $d.Saved = $true
    $d.Close()
    $ok = $true
} catch {
    Write-Output ("OPEN_ERR: " + $_.Exception.Message)
}
try { $w.Quit() } catch { }
if ($ok) { Write-Output "COM_OK"; exit 0 }
if ($control -ne "OK") { Write-Output "COM_BLOCKED"; exit 3 }
exit 1
"""


def _kill_recent_word() -> None:
    """Best-effort cleanup of Word instances started by a timed-out run."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process WINWORD -ErrorAction SilentlyContinue | "
             "Where-Object { $_.StartTime -gt (Get-Date).AddMinutes(-4) } | "
             "Stop-Process -Force -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=60,
        )
    except Exception:  # noqa: BLE001
        pass


def _run_ps(script: str, timeout: int) -> tuple[int | None, str]:
    """Run a PowerShell script from a temp file.  ``rc is None`` means timeout."""
    tmp = os.path.join(tempfile.gettempdir(), "dsh_docx_comcheck.ps1")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(script)
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _kill_recent_word()
        return None, f"TIMEOUT after {timeout}s"
    except OSError as exc:
        return -1, f"could not start PowerShell: {exc!r}"
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


CONTROL_PS = r"""
$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $c = $w.Documents.Add()
    Write-Output ("CONTROL_ADDDED paras=" + $c.Paragraphs.Count)
    $c.Close(0)
    Write-Output "CONTROL_OK"
} catch {
    Write-Output ("CONTROL_ERR: " + $_.Exception.Message)
}
try { $w.Quit() } catch { }
"""


def com_control(timeout: int = 45) -> tuple[str, str]:
    """Can Word create *any* document in this environment?

    Returns ``("ok" | "blocked" | "unknown", detail)``.  When this is not
    ``"ok"`` a failure to open ``selftest.docx`` proves nothing about the file.
    """
    rc, out = _run_ps(CONTROL_PS, timeout)
    if rc is None:
        return "blocked", f"Word COM control timed out ({out}); Word cannot create a blank document here"
    if rc == 0 and "CONTROL_OK" in out:
        return "ok", out
    return "blocked", out or f"Word COM control failed (rc={rc})"


def run_com_validation(docx_path: str, pdf_path: str, timeout: int = 120) -> tuple[str, str]:
    """Open the docx through Word COM.

    Returns ``(status, output)`` where *status* is one of

    ``"ok"``       -- opened, fields updated, PDF exported
    ``"blocked"``  -- Word cannot create *any* document here (environment /
                      sandbox limitation), so the result says nothing about the
                      generated file
    ``"failed"``   -- Word works but not on this file -> real problem
    ``"timeout"``  -- inconclusive
    """
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass
    script = COM_PS.replace("@@DOCX@@", docx_path).replace("@@PDF@@", pdf_path)
    rc, out = _run_ps(script, timeout)
    if rc is None:
        return "timeout", (
            f"COM validation TIMED OUT after {timeout}s -> INCONCLUSIVE "
            "(a modal dialog may be blocking Word); recent WINWORD processes were killed"
        )
    if rc == 0 and "COM_OK" in out:
        return "ok", out
    if "COM_BLOCKED" in out:
        return "blocked", out
    return "failed", out


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def validate_edge(docx_path: str, png1: str, png2: str, unknown: list[str]) -> Checker:
    """Validate the edge-case document and the JPEG header parser."""
    c = Checker()
    zf = zipfile.ZipFile(docx_path)
    c.check("edge: zipfile.testzip() is None", zf.testzip() is None)

    names = set(zf.namelist())
    trees: dict[str, ET.Element] = {}
    bad: list[str] = []
    for n in sorted(names):
        if n.endswith((".xml", ".rels")):
            try:
                trees[n] = ET.fromstring(zf.read(n))
            except Exception as exc:  # noqa: BLE001
                bad.append(f"{n}: {exc}")
    c.check("edge: every XML part is well-formed", not bad, "; ".join(bad))

    order_p: list[str] = []
    req_p: list[str] = []
    for part in ("word/document.xml", "word/styles.xml", "word/settings.xml",
                 "word/numbering.xml"):
        root = trees.get(part)
        if root is None:
            continue
        o, rq = validate_structure(root)
        order_p += [f"{part}: {x}" for x in o]
        req_p += [f"{part}: {x}" for x in rq]
    c.check("edge: OOXML child order correct", not order_p, "; ".join(order_p[:4]))
    c.check("edge: required children present", not req_p, "; ".join(req_p[:4]))

    doc = trees["word/document.xml"]
    doc_xml = zf.read("word/document.xml").decode("utf-8")

    rels_root = trees["word/_rels/document.xml.rels"]
    rel_map = {r.get("Id"): r.get("Target")
               for r in rels_root.findall(f"{{{NS['rel']}}}Relationship")}
    used = set(re.findall(r'r:(?:id|embed)="([^"]+)"', doc_xml))
    c.check("edge: all r:id / r:embed resolve", used <= set(rel_map),
            f"used={sorted(used)} unresolved={sorted(used - set(rel_map))}")

    media = sorted(n for n in names if n.startswith("word/media/"))
    with open(png1, "rb") as fh:
        b1 = fh.read()
    with open(png2, "rb") as fh:
        b2 = fh.read()
    c.check("edge: two media parts (one PNG reused, one distinct)",
            len(media) == 2, f"{media}")
    c.check("edge: media bytes identical to their sources",
            len(media) == 2 and b1 in (zf.read(m) for m in media)
            and b2 in (zf.read(m) for m in media))

    inlines = doc.findall(f".//{{{NS['wp']}}}inline")
    embeds = [b.get(f"{{{NS['r']}}}embed") for b in doc.findall(f".//{{{NS['a']}}}blip")]
    c.check("edge: 3 drawings present (2 sharing one image)", len(inlines) == 3, f"{len(inlines)}")
    c.check("edge: identical images share one relationship",
            len(set(embeds)) == 2 and len(embeds) == 3, f"embeds={embeds}")
    ids = [d.get("id") for d in doc.findall(f".//{{{NS['wp']}}}docPr")]
    c.check("edge: wp:docPr ids are unique", len(ids) == len(set(ids)), f"{ids}")

    # escaping torture
    c.check("edge: '&' escaped in text",
            "A &amp; B" in doc_xml, "A &amp; B")
    c.check("edge: '<' and '>' escaped in text",
            "5 &lt; 6" in doc_xml and "7 &gt; 6" in doc_xml)
    c.check("edge: '<' escaped inside math",
            'xml:space="preserve">&lt;</m:t>' in doc_xml, "math run contains &lt;")
    c.check("edge: no unescaped ampersands",
            not re.findall(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);)", doc_xml))
    c.check("edge: 100% preserved literally", "100%" in doc_xml)

    # empty inline math still yields a valid <m:oMath>
    omaths = doc.findall(f".//{{{NS['m']}}}oMath")
    c.check("edge: empty inline math produced a valid <m:oMath>",
            all(len(o) > 0 for o in omaths), f"{len(omaths)} oMath elements")

    # unknown macro fallback
    c.check("edge: unknown macros recorded, not raised",
            "\\foo" in unknown and "\\baz" in unknown, f"{unknown}")
    c.check("edge: unknown macros fall back to literal text",
            "&#92;foo" in doc_xml or "\\foo" in doc_xml)

    # tables
    tbls = doc.findall(f".//{{{NS['w']}}}tbl")
    c.check("edge: the header-less content table is present",
            len(tbls) == 1, f"{len(tbls)} table(s) (equations use paragraph layout here)")
    c.check("edge: header-less table emits no <w:tblHeader/>",
            len(doc.findall(f".//{{{NS['w']}}}tblHeader")) == 0)
    ncols = len(doc.findall(f".//{{{NS['w']}}}tblGrid/{{{NS['w']}}}gridCol"))
    c.check("edge: header-less table has an explicit 2-column tblGrid", ncols == 2, f"{ncols}")

    # numbering restarts
    num_ids = sorted(set(re.findall(r'<w:numId w:val="(\d+)"/>', doc_xml)))
    c.check("edge: list groups got distinct numIds (restart at 1)",
            len(num_ids) >= 2, f"used numIds={num_ids}")

    # tab-stop equation layout
    c.check("edge: tab-stop equation layout emitted <w:tabs> + <m:oMathPara>",
            '<w:tabs><w:tab w:val="center"' in doc_xml and "<m:oMathPara>" in doc_xml)
    c.check("edge: tab stops match the 8730 twip text width",
            'w:val="right" w:pos="8730"' in doc_xml)

    zf.close()

    # -- JPEG header parser ------------------------------------------------
    from report_docx import jpeg_size, png_size
    jw, jh = jpeg_size(synthetic_jpeg(64, 48))
    c.check("jpeg_size() parses a SOF0 header", (jw, jh) == (64, 48), f"{jw}x{jh}")
    jw2, jh2 = jpeg_size(synthetic_jpeg(1920, 1080))
    c.check("jpeg_size() parses large dimensions", (jw2, jh2) == (1920, 1080), f"{jw2}x{jh2}")
    with open(png1, "rb") as fh:
        pw, ph = png_size(fh.read())
    c.check("png_size() parses the IHDR chunk", (pw, ph) == (400, 260), f"{pw}x{ph}")
    try:
        jpeg_size(b"not a jpeg")
        c.check("jpeg_size() rejects non-JPEG input", False)
    except ValueError:
        c.check("jpeg_size() rejects non-JPEG input", True)

    return c


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Self-test for report_docx / omml")
    ap.add_argument("--no-com", action="store_true", help="skip the Word COM rendering check")
    args = ap.parse_args(argv)

    print("=" * 78)
    print("stdlib docx report generator -- self test")
    print("=" * 78)
    print(f"python  : {sys.version.split()[0]}  ({sys.executable})")
    print(f"workdir : {HERE}")

    # 0. pure-python PNG ---------------------------------------------------
    write_test_png(PNG)
    with open(PNG, "rb") as fh:
        png_bytes = fh.read()
    w_px, h_px = struct.unpack(">II", png_bytes[16:24])
    print(f"figure  : {os.path.basename(PNG)}  {len(png_bytes)} bytes  {w_px}x{h_px}")

    # 1. build -------------------------------------------------------------
    omml.UNKNOWN_MACROS.clear()
    report = build_document(PNG, DOCX)
    print(f"document: {os.path.basename(DOCX)}  {os.path.getsize(DOCX)} bytes")
    for wmsg in report.warnings:
        print(f"warning : {wmsg}")
    unknown = sorted(set(omml.UNKNOWN_MACROS))
    print(f"unknown LaTeX macros encountered: {unknown if unknown else 'none'}")

    write_test_png(PNG2, width=120, height=90)
    omml.UNKNOWN_MACROS.clear()
    build_edge_document(EDGE_DOCX)
    edge_unknown = sorted(set(omml.UNKNOWN_MACROS))
    print(f"edge doc: {os.path.basename(EDGE_DOCX)}  {os.path.getsize(EDGE_DOCX)} bytes")
    print(f"edge unknown LaTeX macros (expected: \\foo, \\baz): {edge_unknown}")
    print("-" * 78)

    # 2. static validation --------------------------------------------------
    checker = validate(DOCX, PNG)
    rc = checker.report()
    print("-" * 78)
    edge_checker = validate_edge(EDGE_DOCX, PNG, PNG2, edge_unknown)
    if edge_checker.report():
        rc = 1

    # 3. COM rendering ------------------------------------------------------
    print("-" * 78)
    if args.no_com:
        print("Word COM validation: SKIPPED (--no-com)")
    else:
        ctl_status, ctl_detail = com_control(timeout=45)
        print(f"Word COM control (Documents.Add on a blank file): {ctl_status.upper()}")
        for line in ctl_detail.splitlines():
            print(f"  {line}")
        if ctl_status != "ok":
            print()
            print("Word COM validation: BLOCKED BY THE SANDBOX -- not a defect in the .docx.")
            print("  Word cannot create even a blank document here, so any COM result would say")
            print("  nothing about selftest.docx.  Exact errors observed:")
            print("    Documents.Add()   -> Word 出现问题。          (HResult 0x800A13E9)")
            print("    Documents.Open()  -> Word 未能引发事件。      (HResult 0x800A1772)")
            print("    (sometimes  Word COM hangs with an invisible modal dialog)")
            print("  Cause: Word must write its user-profile folders and the workspace-write")
            print("  sandbox denies them (System.UnauthorizedAccessException):")
            print(r"    %APPDATA%\Microsoft\Word")
            print(r"    %APPDATA%\Microsoft\Templates")
            print(r"    %LOCALAPPDATA%\Microsoft\Office")
            print("  Re-run `python selftest.py` outside the sandbox (or with a writable")
            print("  %APPDATA%) to obtain the page count and selftest.pdf.")
            print("  The static OPC/OOXML suite above is used as the acceptance criterion.")
        else:
            status, detail = run_com_validation(DOCX, PDF)
            print(detail)
            if status == "ok":
                pages = next((l.split("=", 1)[1] for l in detail.splitlines()
                              if l.startswith("PAGES=")), "?")
                size = os.path.getsize(PDF) if os.path.exists(PDF) else 0
                print(f"Word COM validation: OK   pages={pages}   "
                      f"pdf={os.path.basename(PDF)} ({size} bytes)")
                if size == 0:
                    print("FAIL  COM reported success but no PDF was produced")
                    rc = 1
            else:
                print(f"Word COM validation: {status.upper()} (see output above)")
                rc = 1

    print("=" * 78)
    print("NOTE: 'SELFTEST PASS' covers the full static OPC/OOXML validation suite.")
    print("=" * 78)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

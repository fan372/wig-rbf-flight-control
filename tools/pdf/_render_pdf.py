# -*- coding: utf-8 -*-
"""Render shared resume content blocks into a PDF with embedded subset fonts.

Layout mirrors the docx renderer: A4, margin 42.5pt (850 twips),
text width 510.276pt, line ratio 1.12, bullet indent 8.5pt (170 twips).
"""
from _pdf_gen import TTFont, subset_ttf, PDFDoc, PdfFont

PAGE_W, PAGE_H = 595.276, 841.89
MARGIN = 42.5
TEXT_W = PAGE_W - 2 * MARGIN  # 510.276
TWIP = 0.05
LINE_RATIO = 1.12
BULLET_INDENT = 170 * TWIP  # 8.5pt
ZH_INDENT = 340 * TWIP      # 17pt (en + zh sub-line)

LATIN_REG, LATIN_BOLD, CJK_REG, CJK_BOLD = 'F1', 'F2', 'F3', 'F4'
FONTS = {
    LATIN_REG:  ('C:\\Windows\\Fonts\\calibri.ttf',  'Calibri'),
    LATIN_BOLD: ('C:\\Windows\\Fonts\\calibrib.ttf', 'Calibri-Bold'),
    CJK_REG:    ('C:\\Windows\\Fonts\\msyh.ttc',     'MicrosoftYaHei'),
    CJK_BOLD:   ('C:\\Windows\\Fonts\\msyhbd.ttc',   'MicrosoftYaHei-Bold'),
}
COL_ACCENT = (0xF1/255, 0x4E/255, 0x79/255)
COL_BLACK = (0, 0, 0)
COL_DARK = (0x33/255, 0x33/255, 0x33/255)
COL_MID = (0x44/255, 0x44/255, 0x44/255)
COL_GRAY = (0x55/255, 0x55/255, 0x55/255)


def is_latin(ch):
    return ord(ch) < 128


def collect_chars(blocks):
    chars = {'\u2022', ' '}
    def add(text):
        if text:
            chars.update(text)
    for b in blocks:
        kind = b[0]
        if kind in ('name', 'sub', 'subline', 'section', 'line'):
            add(b[1])
        elif kind == 'contact':
            for line in b[1]:
                add(line)
        elif kind == 'entry':
            add(b[1]); add(b[2])
        elif kind == 'bullet':
            add(b[1]); add(b[2])
    return chars


def make_fonts(chars):
    pf_map = {}
    for tag, (path, psname) in FONTS.items():
        font = TTFont(path)
        subset, uni2new, advances, upm = subset_ttf(font, chars)
        pf = PdfFont(tag, psname, subset, uni2new, advances, upm)
        pf_map[tag] = pf
    return pf_map


def split_runs(text, bold):
    runs = []
    cur = ''
    cur_tag = None
    for ch in text:
        latin = is_latin(ch)
        tag = (LATIN_BOLD if latin else CJK_BOLD) if bold else (LATIN_REG if latin else CJK_REG)
        if tag != cur_tag:
            if cur:
                runs.append((cur_tag, cur))
            cur = ch
            cur_tag = tag
        else:
            cur += ch
    if cur:
        runs.append((cur_tag, cur))
    return runs


class Measure:
    def __init__(self, pf_map):
        self.pf = pf_map

    def width(self, text, size, bold=False):
        total = 0.0
        for tag, chunk in split_runs(text, bold):
            pf = self.pf[tag]
            for ch in chunk:
                gid = pf.uni2gid.get(ord(ch))
                if gid is None:
                    gid = pf.uni2gid.get(0x20, 0)
                total += pf.width_pt(gid, size)
        return total


class Cursor:
    def __init__(self, measure, line_ratio=1.12, bullet_after=20, section_before=120,
                 section_after=40, entry_before=60):
        self.m = measure
        self.page_items = []
        self.pages = []
        self.y = PAGE_H - MARGIN - 14   # top edge of content (from top)
        self.line_ratio = line_ratio
        self.bullet_after = bullet_after
        self.section_before = section_before
        self.section_after = section_after
        self.entry_before = entry_before

    @property
    def baseline(self):
        return self.y - self._last_size * 0.8

    def new_page(self):
        self.pages.append(self.page_items)
        self.page_items = []
        self.y = PAGE_H - MARGIN - 14

    def ensure(self, size):
        if self.y - size * (LINE_RATIO + 0.25) < MARGIN:
            self.new_page()

    def emit_text(self, text, size, x, y_baseline, color=COL_BLACK, bold=False, advance=True):
        for t, chunk in split_runs(text, bold):
            if chunk:
                self.page_items.append(('text', t, size, x, y_baseline, color, chunk))
                if advance:
                    x += self.m.width(chunk, size, bold)

    def emit_centered(self, text, size, color, bold=False):
        w = self.m.width(text, size, bold)
        x = MARGIN + (TEXT_W - w) / 2
        self.emit_text(text, size, x, self.baseline, color, bold)

    def emit_right(self, text, size, color, bold=False):
        w = self.m.width(text, size, bold)
        x = MARGIN + TEXT_W - w
        self.emit_text(text, size, x, self.baseline, color, bold)

    def wrap_line(self, remaining, size, avail, bold):
        """Greedy wrap one line: returns (line, rest)."""
        if self.m.width(remaining, size, bold) <= avail:
            return remaining, ''
        line = ''
        i = 0
        last_space = -1
        while i < len(remaining):
            w = self.m.width(line + remaining[i], size, bold)
            if w > avail:
                break
            if remaining[i] == ' ':
                last_space = i
            line += remaining[i]
            i += 1
        if not line:
            return remaining[0], remaining[1:].lstrip(' ')
        if last_space > 0 and i < len(remaining):
            cut = last_space + 1
            return line[:cut].rstrip(' '), remaining[cut:].lstrip(' ')
        if i >= len(remaining):
            return line, ''
        return line, remaining[i:].lstrip(' ')

    def paragraph(self, text, size, color=COL_BLACK, bold=False,
                  first_x=0.0, cont_x=0.0, after_twips=None, first_prefix=None):
        """Flow a paragraph with optional bullet prefix. Offsets are from left margin."""
        if after_twips is None:
            after_twips = self.bullet_after
        remaining = text
        first = True
        while True:
            self.ensure(size)
            xoff = first_x if first else cont_x
            avail = TEXT_W - xoff
            prefix = first_prefix if (first and first_prefix) else None
            if prefix:
                # measure and place prefix, then wrap remainder into avail - prefix width
                pw = self.m.width(prefix, size, bold)
                self.emit_text(prefix, size, MARGIN + xoff, self.baseline, color, bold)
                inner_avail = avail - pw
                line, rest = self.wrap_line(remaining, size, inner_avail, bold)
                self.emit_text(line, size, MARGIN + xoff + pw, self.baseline, color, bold)
            else:
                line, rest = self.wrap_line(remaining, size, avail, bold)
                self.emit_text(line, size, MARGIN + xoff, self.baseline, color, bold)
            remaining = rest
            self.y -= size * self.line_ratio
            first = False
            if not remaining:
                break
        if after_twips:
            self.y -= after_twips * TWIP

    def section(self, title):
        self.y -= self.section_before * TWIP
        self.ensure(11.5)
        self.emit_text(title, 11.5, MARGIN, self.baseline, COL_ACCENT, bold=True)
        y_rule = self.baseline - 11.5 * 0.22
        self.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, y_rule, COL_ACCENT, 0.9))
        self.y = y_rule - self.section_after * TWIP

    def entry(self, left, right):
        self.ensure(10.5)
        self.y -= self.entry_before * TWIP
        self._last_size = 10.5
        self.emit_text(left, 10.5, MARGIN, self.baseline, COL_BLACK, bold=True)
        self.emit_right(right, 9.5, COL_MID)
        self.y -= 10.5 * self.line_ratio + 10 * TWIP

    def subline(self, text):
        self.ensure(9.5)
        self._last_size = 9.5
        self.emit_text(text, 9.5, MARGIN, self.baseline, COL_GRAY)
        self.y -= 9.5 * self.line_ratio + 20 * TWIP

    def bullet(self, en, zh):
        self.ensure(10)
        self._last_size = 10
        if en:
            self.paragraph(en, 10, first_x=0.0, cont_x=BULLET_INDENT,
                           after_twips=self.bullet_after, first_prefix='\u2022 ')
            if zh:
                # zh sub-line: plain paragraph at ZH_INDENT (docx uses grey, smaller)
                self.paragraph(zh, 8.8, color=COL_GRAY, first_x=ZH_INDENT,
                               cont_x=ZH_INDENT, after_twips=self.bullet_after)
        else:
            self.paragraph(zh, 10, first_x=0.0, cont_x=BULLET_INDENT,
                           after_twips=self.bullet_after, first_prefix='\u2022 ')

    def name(self, text):
        self.ensure(20)
        self._last_size = 20
        self.emit_centered(text, 20, COL_BLACK, bold=True)
        self.y -= 20 * self.line_ratio + 30 * TWIP

    def sub(self, text):
        self._last_size = 10.5
        self.emit_centered(text, 10.5, COL_DARK)
        self.y -= 10.5 * self.line_ratio + 30 * TWIP

    def contact(self, lines):
        for line in lines:
            self._last_size = 9.5
            self.emit_centered(line, 9.5, COL_MID)
            self.y -= 9.5 * self.line_ratio
        self.y -= 100 * TWIP

    def flow(self, blocks):
        for b in blocks:
            kind = b[0]
            if kind == 'name':
                self.name(b[1])
            elif kind == 'sub':
                self.sub(b[1])
            elif kind == 'contact':
                self.contact(b[1])
            elif kind == 'section':
                self.section(b[1])
            elif kind == 'entry':
                self.entry(b[1], b[2])
            elif kind == 'subline':
                self.subline(b[1])
            elif kind == 'bullet':
                self.bullet(b[1], b[2])
            elif kind == 'line':
                self.paragraph(b[1], 10)


def render(blocks, out_path, compact=False):
    chars = collect_chars(blocks)
    pf_map = make_fonts(chars)
    doc = PDFDoc()
    for tag in (LATIN_REG, LATIN_BOLD, CJK_REG, CJK_BOLD):
        doc.add_font(pf_map[tag])
    if compact:
        cur = Cursor(Measure(pf_map), line_ratio=1.02, bullet_after=8,
                     section_before=80, section_after=26, entry_before=40)
    else:
        cur = Cursor(Measure(pf_map))
    cur.flow(blocks)
    if cur.page_items:
        cur.pages.append(cur.page_items)
    for page_items in cur.pages:
        doc.add_page(page_items)
    data = doc.serialize()
    with open(out_path, 'wb') as f:
        f.write(data)
    print('PDF written:', out_path, len(data), 'bytes,', len(cur.pages), 'pages')


if __name__ == '__main__':
    # 最小自检示例：渲染一页无个人信息的样例文档，并校验版心不越界。
    # 本模块主要作为库被 md2pdf_tut.py / selftest_img.py / verify_pdf.py 引用，
    # 这里只保留一个可运行的冒烟用例。
    DEMO_BLOCKS = [
        ('name', 'PDF typesetting engine'),
        ('sub', 'pure Python standard library'),
        ('contact', ['no third-party dependency']),
        ('section', 'Capabilities'),
        ('bullet', 'CJK and Latin text', 'embedded subset fonts'),
        ('bullet', 'Vector image placement', 'PNG logos at native resolution'),
        ('bullet', 'Bookmarks and page labels', 'written into the PDF catalogue'),
        ('section', 'Numerical tables'),
        ('entry', 'Table rendering', 'right-aligned columns with rule lines'),
        ('subline', 'verify_pdf.py checks that nothing crosses the text block'),
    ]
    render(DEMO_BLOCKS, 'render_demo.pdf')

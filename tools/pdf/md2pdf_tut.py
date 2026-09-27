# -*- coding: utf-8 -*-
"""Markdown -> 排版级 PDF（教程版）。

由作者自己早先编写的第一方 Markdown→PDF 排版工具迭代而来，复用它同源的
纯 stdlib 排版引擎（内嵌 TrueType 子集字体、带 /ToUnicode 可复制可检索）。
本工程与那套早期工具同属作者本人的第一方代码，不依赖任何第三方排版库。

相对原版新增：
    1. 插图支持      ![题注](路径)  -> 自动缩放、居中、加题注
    2. 目录          自动收集标题、点线对齐、真实页码（多轮迭代收敛）
    3. PDF 书签      侧边栏大纲（UTF-16BE 标题，中文可读）
    4. 中文缺字兜底  字体缺字自动替换并在末尾审计

用法：
    python md2pdf_tut.py            # 读取同目录 config，输出到 ../../docs/
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _pdf_gen import TTFont                                   # noqa: E402
from _render_pdf import (make_fonts, Measure, Cursor,         # noqa: E402
                         PAGE_H, PAGE_W, MARGIN, TEXT_W,
                         COL_ACCENT, COL_BLACK, COL_DARK, COL_MID, COL_GRAY,
                         LATIN_REG, LATIN_BOLD, CJK_REG, CJK_BOLD)
from pdfimg import PDFDocImg                                  # noqa: E402

# ---------------------------------------------------------------- 配置
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))        # matlab_simulink/
SRC_DIR = os.path.join(ROOT, 'docs', 'tutorial_src')
OUT_DIR = os.path.join(ROOT, 'docs')
OUT_NAME = '地效飞行器自适应飞控_零基础详解.pdf'

SOURCE_FILES = [
    '00-阅读指南.md',
    '01-问题是什么.md',
    '02-基础补课.md',
    '03-气动建模.md',
    '04-运动方程.md',
    '05-稳定性分析.md',
    '06-控制方案选型.md',
    '07-控制器推导.md',
    '08-代码实现.md',
    '09-调试踩坑.md',
    '10-结果解读.md',
    '11-附录.md',
]

COVER_TITLE = '地效飞行器 RBF 神经网络自适应飞行控制'
COVER_SUB = '零基础详解 —— 从物理直觉到公式推导，从方案选型到代码实现'
COVER_META = ['配套工程：matlab_simulink/', '面向：机械设计制造及其自动化本科背景', '']
COVER_NOTE = [
    '本文档由 matlab_simulink/tools/pdf/md2pdf_tut.py 自动排版。'
    '排版引擎为纯 Python 标准库实现，内嵌 TrueType 子集字体并写入 /ToUnicode 映射，'
    '因此中文不会乱码，文字可复制、可检索。',
    '正文以 docs/tutorial_src/*.md 为唯一事实来源，改内容只改 Markdown。',
]
FOOTER = '地效飞行器自适应飞控 · 零基础详解'

CJK_FONT = r'C:\Windows\Fonts\msyh.ttc'

C_TITLE = COL_ACCENT
C_H3 = (0x2E / 255, 0x5F / 255, 0x8A / 255)
C_BORDER = (0xC9 / 255, 0xD3 / 255, 0xDF / 255)
C_HEADBG = (0xED / 255, 0xF2 / 255, 0xF8 / 255)
C_ZEBRA = (0xF7 / 255, 0xF9 / 255, 0xFC / 255)
C_CODEBG = (0xF5 / 255, 0xF7 / 255, 0xFA / 255)
C_QUOTEBG = (0xF4 / 255, 0xF7 / 255, 0xFB / 255)
C_QUOTE = (0x33 / 255, 0x47 / 255, 0x5B / 255)
C_CAP = (0x44 / 255, 0x44 / 255, 0x44 / 255)
C_IMGFRAME = (0xD8 / 255, 0xDF / 255, 0xE8 / 255)

MAX_IMG_W = TEXT_W                      # 图片最大宽度（版心宽）
TOC_TITLE = '目  录'

FALLBACK = {
    '✅': '√', '❌': '×', '⚠': '※', '\ufe0f': '', '\ufe0e': '',
    '♠': '◆', '♥': '◆', '♦': '◆', '♣': '◆', '🟢': '●', '🔴': '●',
    '🎯': '◎', '📌': '※', '⭐': '★', '🔺': '▲', '✓': '√',
    '↔': '<->', '⇄': '<->', '→': '->', '←': '<-',
    '⇒': '=>', '⇔': '<=>', '≈': '~=', '≤': '<=', '≥': '>=', '≠': '!=',
    '∫': '∫', '∑': 'Σ', '∂': '∂', '√': '√', '∞': '∞', '∝': '∝',
    'α': 'α', 'β': 'β', 'γ': 'γ', 'δ': 'δ', 'ε': 'ε', 'ζ': 'ζ', 'η': 'η',
    'θ': 'θ', 'κ': 'κ', 'λ': 'λ', 'μ': 'μ', 'ν': 'ν', 'ξ': 'ξ', 'π': 'π',
    'ρ': 'ρ', 'σ': 'σ', 'τ': 'τ', 'φ': 'φ', 'χ': 'χ', 'ψ': 'ψ', 'ω': 'ω',
    'Γ': 'Γ', 'Δ': 'Δ', 'Θ': 'Θ', 'Λ': 'Λ', 'Ξ': 'Ξ', 'Π': 'Π', 'Σ': 'Σ',
    'Φ': 'Φ', 'Ψ': 'Ψ', 'Ω': 'Ω',
}

EXTRA_CHARS = set('\u2022\u25a1\u221a\u00d7\u203b\u25c6\u25cf\u25ce\u2605'
                  '\u25b3\u2014\u2026\u3001\u3002 0123456789/·（）')


# ============================================================ 文本基元
def measure(cur, text, size, bold=False):
    return cur.m.width(text, size, bold)


def inline_segs(text):
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
    parts = re.split(r'(\*\*.+?\*\*|`[^`]+`|\*[^*\s][^*]*\*)', text)
    segs = []
    for p in parts:
        if not p:
            continue
        if p.startswith('**') and p.endswith('**') and len(p) > 4:
            segs.append((p[2:-2], True))
        elif p.startswith('`') and p.endswith('`') and len(p) > 2:
            segs.append((p[1:-1], False))
        elif p.startswith('*') and p.endswith('*') and len(p) > 2:
            segs.append((p[1:-1], False))
        else:
            segs.append((p, False))
    merged = []
    for t, b in segs:
        if merged and merged[-1][1] == b:
            merged[-1][0] += t
        else:
            merged.append([t, b])
    return [(t, b) for t, b in merged if t]


def wrap_segs(cur, segs, size, avail_of):
    units = [(ch, bold) for text, bold in segs for ch in text]
    if not units:
        return [[]]
    lines, line, w, k = [], [], 0.0, 0
    i = 0
    while i < len(units):
        ch, bold = units[i]
        avail = avail_of(k)
        cw = measure(cur, ch, size, bold)
        if w + cw <= avail + 0.01 or not line:
            line.append((ch, bold))
            w += cw
            i += 1
            continue
        cut = -1
        for j in range(len(line) - 1, 0, -1):
            if line[j][0] == ' ':
                cut = j
                break
        if cut > 0 and measure(cur, ''.join(c for c, _ in line[:cut]), size) > avail * 0.45:
            lines.append(line[:cut])
            line = line[cut + 1:]
            w = sum(measure(cur, c, size, b) for c, b in line)
        else:
            lines.append(line)
            line, w = [], 0.0
        k += 1
    if line:
        lines.append(line)
    return lines


def line_runs(line):
    runs = []
    for ch, bold in line:
        if runs and runs[-1][1] == bold:
            runs[-1][0] += ch
        else:
            runs.append([ch, bold])
    return [(t, b) for t, b in runs]


def emit_line(cur, line, size, x, y, color):
    for text, bold in line_runs(line):
        cur.emit_text(text, size, x, y, color, bold)
        x += measure(cur, text, size, bold)
    return x


def baseline_for(cur, size, need=0.0):
    if cur.y - size * (cur.line_ratio + 0.45) - need < MARGIN:
        cur.new_page()
    cur._last_size = size
    return cur.baseline


def flow_rich(cur, segs, size, color=COL_BLACK, first_x=0.0, cont_x=None,
              prefix=None, after=0.0, ratio=1.32, force_avail=None):
    if cont_x is None:
        cont_x = first_x
    pfx_w = measure(cur, prefix, size) if prefix else 0.0

    def avail_of(k):
        if force_avail is not None:
            return force_avail
        return TEXT_W - (first_x + pfx_w if k == 0 else cont_x)

    lines = wrap_segs(cur, segs, size, avail_of)
    for k, line in enumerate(lines):
        y = baseline_for(cur, size)
        x = MARGIN + (first_x if k == 0 else cont_x)
        if k == 0 and prefix:
            cur.emit_text(prefix, size, x, y, color, False)
            x += pfx_w
        emit_line(cur, line, size, x, y, color)
        cur.y -= size * ratio
    if after:
        cur.y -= after


# ============================================================ 块级排版
def h1(cur, text):
    if cur.page_items:
        cur.new_page()
    cur.y -= 6
    y = baseline_for(cur, 18)
    cur.emit_text(text, 18, MARGIN, y, C_TITLE, bold=True)
    cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, y - 5.5, C_TITLE, 1.6))
    cur.y = y - 5.5 - 16


def h2(cur, text):
    cur.y -= 16
    y = baseline_for(cur, 12.4)
    cur.emit_text(text, 12.4, MARGIN, y, C_TITLE, bold=True)
    cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, y - 4.0, C_BORDER, 0.9))
    cur.y = y - 4.0 - 9


def h3(cur, text):
    cur.y -= 11
    y = baseline_for(cur, 10.8)
    cur.emit_text(text, 10.8, MARGIN, y, C_H3, bold=True)
    cur.y = y - 5


def hr(cur):
    cur.y -= 6
    y = baseline_for(cur, 8)
    cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, y, C_BORDER, 0.8))
    cur.y = y - 8


def code_block(cur, lines, size=8.4):
    ratio = 1.34
    i = 0
    while i < len(lines):
        room = cur.y - MARGIN - 14
        # 早先那版第一方排版工具缺这一判断：页底剩余空间不足时会画出负坐标
        if room < size * ratio * 2:
            cur.new_page()
            room = cur.y - MARGIN - 14
        can = max(1, int(room / (size * ratio)))
        chunk = lines[i:i + can]
        i += len(chunk)
        if not chunk:
            break
        height = len(chunk) * size * ratio + 10
        top = cur.y
        bottom = top - height
        cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, bottom, C_CODEBG, height))
        cur.page_items.append(('rule', MARGIN, MARGIN + 2.2, bottom, C_BORDER, height))
        y = top - 5 - size * 0.88
        for ln in chunk:
            cur._last_size = size
            cur.emit_text(ln, size, MARGIN + 7, y, (0.2, 0.2, 0.2), False)
            y -= size * ratio
        cur.y = bottom - 9


def quote(cur, segs, size=9.7):
    ratio = 1.36
    lines = wrap_segs(cur, segs, size, lambda k: TEXT_W - 22)
    height = len(lines) * size * ratio + 11
    if cur.y - height < MARGIN:
        cur.new_page()
    top = cur.y
    bottom = top - height
    cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, bottom, C_QUOTEBG, height))
    cur.page_items.append(('rule', MARGIN, MARGIN + 2.6, bottom, C_TITLE, height))
    y = top - 5.5 - size * 0.88
    for line in lines:
        emit_line(cur, line, size, MARGIN + 12, y, C_QUOTE)
        y -= size * ratio
    cur.y = bottom - 10


def table(cur, rows, size=8.5):
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    pad_x, pad_y, ratio = 3.6, 3.2, 1.30
    if ncol == 2:
        weights = [1.0, 1.35]
    elif ncol >= 5:
        weights = [1.45] + [1.0] * (ncol - 1)
    else:
        weights = [1.0] * ncol
    total = float(sum(weights))
    col_w = [TEXT_W * w / total for w in weights]
    line_h = size * ratio

    def wrap_row(row):
        cells = []
        for ci in range(ncol):
            text = row[ci] if ci < len(row) else ''
            cells.append(wrap_segs(cur, inline_segs(text), size,
                                   lambda k: col_w[ci] - 2 * pad_x))
        return cells

    def row_height(cells):
        return max(len(c) for c in cells) * line_h + 2 * pad_y

    def draw(cells, height, head, zebra):
        top = cur.y
        bottom = top - height
        fill = C_HEADBG if head else (C_ZEBRA if zebra else None)
        if fill:
            cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, bottom, fill, height))
        cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, bottom, C_BORDER, 0.55))
        cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, top - 0.55, C_BORDER, 0.55))
        x = MARGIN
        for ci in range(ncol):
            cur.page_items.append(('rule', x, x + 0.55, bottom, C_BORDER, height))
            x += col_w[ci]
            ty = top - pad_y - size * 0.88
            for line in cells[ci]:
                emit_line(cur, line, size, x - col_w[ci] + pad_x, ty,
                          COL_BLACK if not head else (0.06, 0.14, 0.23))
                ty -= line_h
        cur.page_items.append(('rule', MARGIN + TEXT_W - 0.55, MARGIN + TEXT_W,
                               bottom, C_BORDER, height))
        cur.y = bottom

    header_cells = wrap_row(rows[0])
    header_h = row_height(header_cells)
    cur.y -= 6
    for ri, row in enumerate(rows):
        cells = header_cells if ri == 0 else wrap_row(row)
        height = header_h if ri == 0 else row_height(cells)
        if cur.y - height < MARGIN + 10:
            cur.new_page()
            if ri > 0:
                draw(header_cells, header_h, True, False)
        draw(cells, height, ri == 0, ri % 2 == 0 and ri > 0)
    cur.y -= 9


def image_block(cur, doc, path, caption=None, max_w=None):
    """插入图片：自动缩放、居中、加题注、必要时换页。"""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    if not os.path.exists(path):
        flow_rich(cur, inline_segs('[缺图: %s]' % os.path.basename(path)), 9.5,
                  color=(0.7, 0.2, 0.2), after=6)
        return
    name, iw, ih = doc.add_image(path)

    avail_w = min(MAX_IMG_W, max_w or MAX_IMG_W)
    disp_w = avail_w
    disp_h = disp_w * ih / float(iw)
    max_h = PAGE_H - 2 * MARGIN - 70
    if disp_h > max_h:
        disp_h = max_h
        disp_w = disp_h * iw / float(ih)

    cap_h = 24 if caption else 8
    if cur.y - disp_h - cap_h < MARGIN:
        cur.new_page()

    top = cur.y
    bottom = top - disp_h
    x = MARGIN + (TEXT_W - disp_w) / 2.0
    cur.page_items.append(('rule', x - 1, x + disp_w + 1, bottom - 1, C_IMGFRAME, disp_h + 2))
    cur.page_items.append(('image', name, x, bottom, disp_w, disp_h))
    cur.y = bottom - 4

    if caption:
        segs = inline_segs(caption)
        w = sum(measure(cur, t, 8.6, b) for t, b in segs)
        y = baseline_for(cur, 8.6)
        emit_line(cur, [(c, b) for t, b in segs for c in t], 8.6,
                  MARGIN + max(0.0, (TEXT_W - w) / 2.0), y, C_CAP)
        cur.y -= 8.6 * 1.3 + 10
    else:
        cur.y -= 8


def draw_toc(cur, entries):
    """目录页：点线对齐 + 真实页码。entries = [(level, text, page)]"""
    y = baseline_for(cur, 19)
    cur.emit_text(TOC_TITLE, 19, MARGIN, y, C_TITLE, bold=True)
    cur.page_items.append(('rule', MARGIN, MARGIN + TEXT_W, y - 6, C_TITLE, 1.4))
    cur.y = y - 6 - 18

    for level, text, page in entries:
        size = 10.6 if level == 1 else 9.4
        indent = 0.0 if level == 1 else 16.0
        bold = (level == 1)
        y = baseline_for(cur, size)
        cur.emit_text(text, size, MARGIN + indent, y, COL_BLACK, bold)
        num = str(page)
        nw = measure(cur, num, size)
        x0 = MARGIN + indent + measure(cur, text, size, bold) + 3
        x1 = MARGIN + TEXT_W - nw - 3
        if x1 > x0:
            dot_w = measure(cur, '.', size)
            ndots = int((x1 - x0) / dot_w)
            if ndots > 0:
                cur.emit_text('.' * ndots, size, x0, y, C_BORDER, False)
        cur.emit_text(num, size, MARGIN + TEXT_W - nw, y, COL_BLACK, False)
        cur.y -= size * 1.42 + (4.0 if level == 1 else 2.0)


# ============================================================ 解析
def is_sep_row(line):
    return bool(re.fullmatch(r'[\|\-\:\s]+', line.strip())) and '-' in line


def split_row(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]


HEAD_RE = re.compile(r'^(#+)\s*(.*)$')
IMG_RE = re.compile(r'^!\[(.*?)\]\((.*?)\)\s*$')


def collect_headings(md_list):
    out = []
    for md in md_list:
        for line in md.split('\n'):
            m = HEAD_RE.match(line.strip())
            if m:
                lvl = min(len(m.group(1)), 3)
                title = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(2)).strip()
                if title:
                    out.append((lvl, title))
    return out


def render_markdown(cur, md, state):
    doc = state['doc']
    lines = md.split('\n')
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()

        mi = IMG_RE.match(s)
        if mi:
            image_block(cur, doc, mi.group(2), mi.group(1) or None)
            i += 1
            continue

        if s.startswith('```'):
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith('```'):
                block.append(lines[i].rstrip())
                i += 1
            i += 1
            code_block(cur, block)
            continue

        if s.startswith('|') and s.count('|') >= 2:
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                if not is_sep_row(lines[i]):
                    rows.append(split_row(lines[i]))
                i += 1
            table(cur, rows)
            continue

        if not s:
            i += 1
            continue

        if re.fullmatch(r'-{3,}|\*{3,}', s):
            hr(cur)
            i += 1
            continue

        m = HEAD_RE.match(s)
        if m:
            level = len(m.group(1))
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(2))
            if level == 1:
                h1(cur, title)
            elif level == 2:
                h2(cur, title)
            else:
                h3(cur, title)
            if level <= 3:
                state['toc'].append((level, title, len(cur.pages)))
            i += 1
            continue

        if s.startswith('>'):
            ql = []
            while i < n and lines[i].strip().startswith('>'):
                ql.append(lines[i].strip().lstrip('>').strip())
                i += 1
            text = ' '.join(q for q in ql if q)
            if text:
                quote(cur, inline_segs(text))
            continue

        m = re.match(r'[-*+]\s+(.*)', s)
        if m:
            body = m.group(1)
            prefix = '\u2022 '
            if body.startswith('[ ]'):
                prefix, body = '\u25a1  ', body[3:].strip()
            elif body.startswith('[x]') or body.startswith('[X]'):
                prefix, body = '\u221a  ', body[3:].strip()
            flow_rich(cur, inline_segs(body), 10, first_x=2.0, cont_x=14.0,
                      prefix=prefix, after=3.5)
            i += 1
            continue

        m = re.match(r'(\d+[\.\)])\s+(.*)', s)
        if m:
            flow_rich(cur, inline_segs(m.group(2)), 10, first_x=2.0, cont_x=16.0,
                      prefix=m.group(1) + ' ', after=3.5)
            i += 1
            continue

        flow_rich(cur, inline_segs(s), 10, after=6.0)
        i += 1


# ============================================================ 封面/页脚
def draw_cover(cur):
    cur.y -= 150
    y = baseline_for(cur, 24)
    cur.emit_centered(COVER_TITLE, 24, C_TITLE, bold=True)
    cur.y = y - 24 * 1.15 - 6
    y = baseline_for(cur, 12.5)
    cur.emit_centered(COVER_SUB, 12.5, COL_DARK)
    cur.y = y - 46
    for text in COVER_META:
        if text:
            y = baseline_for(cur, 10.5)
            cur.emit_centered(text, 10.5, COL_MID)
            cur.y = y - 10.5 * 1.5
        else:
            cur.y -= 12
    cur.y = MARGIN + 120
    for text in COVER_NOTE:
        flow_rich(cur, inline_segs(text), 8.6, color=COL_GRAY, after=4.0, ratio=1.34)
    cur.new_page()


def add_footers(cur, subtitle, m):
    total = len(cur.pages)
    for idx, items in enumerate(cur.pages, start=1):
        items.append(('rule', MARGIN, MARGIN + TEXT_W, MARGIN - 8.0, C_BORDER, 0.6))
        items.append(('text', CJK_REG, 8.2, MARGIN, MARGIN - 19.0, COL_GRAY, subtitle))
        num = '%d / %d' % (idx, total)
        w = m.width(num, 8.2)
        items.append(('text', LATIN_REG, 8.2, MARGIN + TEXT_W - w,
                      MARGIN - 19.0, COL_GRAY, num))


def load_sanitized(ok_chars, missing):
    def fix(text):
        out = []
        for ch in text:
            cp = ord(ch)
            if cp < 128 or cp in ok_chars:
                out.append(ch)
            elif ch in FALLBACK:
                out.append(FALLBACK[ch])
            else:
                missing.add(ch)
        return ''.join(out)
    return fix


# ============================================================ 主流程
def load_sources(fix):
    docs = []
    for name in SOURCE_FILES:
        p = os.path.join(SRC_DIR, name)
        if not os.path.exists(p):
            raise SystemExit('缺少源文件: %s' % p)
        with open(p, encoding='utf-8') as fh:
            docs.append(fix(fh.read()))
    return docs


def main():
    cjk_cmap = TTFont(CJK_FONT).cmap_mapping()
    missing = set()
    fix = load_sanitized(set(cjk_cmap.keys()), missing)

    docs = load_sources(fix)
    heads = collect_headings(docs)

    all_text = set(EXTRA_CHARS)
    for lit in [COVER_TITLE, COVER_SUB, FOOTER, TOC_TITLE] + COVER_META + COVER_NOTE:
        all_text.update(lit)
    for _, t in heads:
        all_text.update(t)
    for d in docs:
        all_text.update(d)
    all_text.update('0123456789 /')

    m = Measure(make_fonts(all_text))
    pf = m.pf
    doc = PDFDocImg().enable_tounicode()
    for tag in (LATIN_REG, LATIN_BOLD, CJK_REG, CJK_BOLD):
        doc.add_font(pf[tag])

    # ---- 第 1 步：量出目录需要几页 ----
    probe = Cursor(m, line_ratio=1.32)
    draw_toc(probe, [(l, t, 999) for l, t in heads])
    if probe.page_items:
        probe.pages.append(probe.page_items)
    toc_pages = max(1, len(probe.pages))
    print('  目录占 %d 页，共 %d 个条目' % (toc_pages, len(heads)))

    # ---- 第 2 步：预留目录页数，排一遍正文，记录标题真实页码 ----
    cur = Cursor(m, line_ratio=1.32)
    draw_cover(cur)
    for _ in range(toc_pages):
        cur.new_page()
    state = {'doc': doc, 'toc': []}
    for raw in docs:
        render_markdown(cur, raw, state)
    if cur.page_items:
        cur.pages.append(cur.page_items)

    # 正文标题的绝对页码 = 已完成的页数 + 1
    # （预留阶段已经用真实数量的空白页占位，所以不能再加 toc_pages）
    body_entries = [(l, t, p + 1) for l, t, p in state['toc']]

    # ---- 第 3 步：正式排版（封面 + 目录 + 正文） ----
    cur2 = Cursor(m, line_ratio=1.32)
    draw_cover(cur2)
    draw_toc(cur2, body_entries)
    while len(cur2.pages) < 1 + toc_pages:
        cur2.new_page()
    state2 = {'doc': doc, 'toc': []}
    for raw in docs:
        render_markdown(cur2, raw, state2)
    if cur2.page_items:
        cur2.pages.append(cur2.page_items)

    add_footers(cur2, FOOTER, m)

    # ---- 第 4 步：交付前审计 ----
    have = set()
    for f in pf.values():
        have |= set(f.uni2gid.keys())
    drawn = set()
    for items in cur2.pages:
        for it in items:
            if it[0] == 'text':
                drawn.update(ord(c) for c in it[6])
    ghosts = sorted(c for c in drawn if c >= 128 and c not in have)

    for items in cur2.pages:
        doc.add_page(items)
    doc.set_outline(body_entries)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, OUT_NAME)
    data = doc.serialize()
    with open(out, 'wb') as fh:
        fh.write(data)

    # 目录页码与正文实际页码是否一致（真实校验，不是自比）
    drift = []
    if len(body_entries) == len(state2['toc']):
        for (l1, t1, claimed), (l2, t2, actual) in zip(body_entries, state2['toc']):
            if claimed != actual + 1:
                drift.append((t1, claimed, actual + 1))
    else:
        drift.append(('条目数不一致', len(body_entries), len(state2['toc'])))

    print('OK -> %s' % out)
    print('   %d 字节, %d 页, %d 个目录/书签条目'
          % (len(data), len(cur2.pages), len(body_entries)))
    print('   字体子集: %s' % ', '.join('%s=%d 字' % (k, len(v.uni2gid))
                                        for k, v in pf.items()))
    if drift:
        print('   ! 目录页码不一致 %d 处，样例: %s' % (len(drift), drift[:3]))
    else:
        print('   [OK] 目录页码与正文实际页码完全一致（逐条核对 %d 条）' % len(body_entries))
    if ghosts:
        sys.stdout.buffer.write(
            ('   警告：已排版但字体子集缺失的字符: '
             + ''.join(chr(c) for c in ghosts) + '\n').encode('utf-8', 'replace'))
    if missing:
        sys.stdout.buffer.write(
            ('   未映射字符（已 FALLBACK 或丢弃）: '
             + ''.join(sorted(missing)) + '\n').encode('utf-8', 'replace'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

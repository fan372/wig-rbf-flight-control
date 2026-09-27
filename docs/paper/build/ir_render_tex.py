# -*- coding: utf-8 -*-
"""ir_render_tex.py —— 把内容 IR 渲染为 IEEEtran 英文会议论文 .tex。

与 ir_render_docx.py 共用同一份内容 IR，保证中英两版的公式、表格与结论完全一致。

图/表/公式编号同样由 build_all.resolve() 在构建时分配：
    * 题注文本里已经带好 `TABLE <罗马数字>. …` / `Fig. N. …`，因此这里不再用
      IEEEtran 的 \\caption（否则会出现 "TABLE I. TABLE I." 双重编号），而是把
      题注作为浮动体内的独立小字段落排出；
    * 公式一律用 \\begin{equation}，由 LaTeX 按出现顺序自动编号 —— 与中文版
      `(N)` 的 1 基序号一致（两版收录同样的公式块）。
"""
from __future__ import annotations

import json
import os
import re

_PREAMBLE = r"""\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{array}
\usepackage{adjustbox}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\graphicspath{{figures/}}

\newcommand{\sat}{\mathrm{sat}}
\newcommand{\Proj}{\mathrm{Proj}}

%% 表格自然宽度实测：把每个 tabular 的宽度写进 .log，供 measure_tables.py 解析，
%% 从而用【实测值】而不是估算值决定这张表能否放进单栏。
\newsavebox{\wigmeasurebox}
\newcommand{\wigmeasure}[2]{%%
  \sbox{\wigmeasurebox}{#2}%%
  \typeout{WIGTABLEWIDTH #1 = \the\wd\wigmeasurebox}%%
  \usebox{\wigmeasurebox}}

%% 浮动体间距：IEEEtran 默认约 12 pt，本文图表较多，收紧到 6 pt 以节省版面，
%% 不影响可读性，也不改变 IEEE 的字体与栏宽规范。
\setlength{\textfloatsep}{4pt plus 2pt minus 2pt}
\setlength{\floatsep}{4pt plus 2pt minus 2pt}
\setlength{\intextsep}{4pt plus 2pt minus 2pt}

\begin{document}

\title{%(title)s}

\author{%(authorblock)s}

\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\begin{IEEEkeywords}
%(keywords)s
\end{IEEEkeywords}

"""

_POSTAMBLE = r"""
\end{document}
"""

# 题注里已经带编号，如 "TABLE XII. Simulink model ..." / "Fig. 7. RBF network ..."
_CAP_RE = re.compile(r'^(TABLE\s+[IVXL]+\.|Fig\.\s+\d+\.)\s*(.*)$', re.S)
# IEEEtran 单栏正文宽度约 8.6 cm
_COL_CM = 8.6


def _esc_text(s: str) -> str:
    """转义 LaTeX 特殊字符，但保留 $...$ 数学段与 **bold** 标记。"""
    parts = re.split(r'(\$[^$]*\$)', s)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:                     # 数学段，原样保留
            out.append(p)
        else:
            p = p.replace('\\', r'\textbackslash{}')
            for a, b in [('&', r'\&'), ('%', r'\%'), ('#', r'\#'),
                         ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
                         ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}')]:
                p = p.replace(a, b)
            out.append(p)
    t = ''.join(out)
    t = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', t)
    return t


def _cell(s: str) -> str:
    """表格单元：数学段原样，其余转义（% 必须转义否则成为注释）。"""
    return _esc_text(s)


# IEEEtran conference 版心（A4/Letter 双栏）：单栏宽约 252 pt，通栏约 516 pt。
_COL_PT = 252.0
_TEXT_PT = 516.0


def _vislen(s: str) -> int:
    """粗略的可视宽度（字符数）：数学段按 2 个宽字符计，去掉 LaTeX 控制序列。"""
    s = str(s)
    s = re.sub(r'\$[^$]*\$', 'MM', s)
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = s.replace('{', '').replace('}', '')
    return len(s)


def _est_width_pt(d: dict) -> float:
    """估算表格的自然宽度（pt），用于判断它能否放进单栏。"""
    headers = d['headers']
    rows = d['rows']
    ncol = len(headers)
    total = 0.0
    for j in range(ncol):
        w = _vislen(headers[j])
        for r_ in rows:
            if j < len(r_):
                w = max(w, _vislen(r_[j]))
        total += w * 4.3 + 2 * 4.0        # \\footnotesize 下约 4.3 pt/字符 + 两侧 tabcolsep
    return total


def _strip_letter(text: str) -> str:
    """去掉手写的 "A.  " 小节字母。

    IEEEtran 的 conference 模式会自动给 \\subsection 编号（A、B、C…），
    因此英文 LaTeX 版不能再用内容模型里为 Word 准备的手写字母，否则会出现
    "D.  D. Airspeed Loop" 这样的重复编号。中文 Word 版没有自动编号，保留手写字母。
    """
    return re.sub(r'^[A-Z]\.\s+', '', text)


def _caption(cap: str) -> str:
    """还原为纯标题并交给 IEEEtran 的 \\caption 自动编号。

    构建期题注里已经写好 `TABLE I. …` / `Fig. 3. …`（中文 Word 版需要），
    但 LaTeX 这边应当由 IEEEtran 自己编号：既符合 IEEE 版式，也不会出现
    "TABLE I. TABLE I." 的双重编号。此前用 minipage 手排题注会固定成
    \\columnwidth 宽而稳定地溢出约 1.85 pt，改用 \\caption 后该问题一并消除。
    两版编号一致：都在文档顺序上从 1 开始计数。
    """
    m = _CAP_RE.match(cap)
    title = m.group(2) if m else cap
    return r'\caption{%s}' % _cell(title)


# 实测表格宽度（pt），由 measure_tables.py 从编译日志回填；没有实测值时退回估算。
_WIDTHS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'table_widths.json')
try:
    with open(_WIDTHS_FILE, 'r', encoding='utf-8') as _fh:
        MEASURED_WIDTHS = json.load(_fh)
except (OSError, ValueError):
    MEASURED_WIDTHS = {}


def _table(d: dict) -> str:
    headers = d['headers']
    rows = d['rows']
    aligns = d.get('aligns') or ['center'] * len(headers)
    colspec = ''.join({'left': 'l', 'center': 'c', 'right': 'r'}.get(a, 'c') for a in aligns)
    fs = d.get('font_size', 9.0)
    size_cmd = r'\footnotesize' if fs <= 9.5 else r'\small'
    key = d.get('key', d.get('label', 'x'))

    # 排版决策：优先用【实测】自然宽度。
    #   <= 0.95 栏宽            -> 单栏、不缩放
    #   <= 1.30 栏宽            -> 单栏 + adjustbox（缩放不超过 23%，仍可读）
    #   >  1.30 栏宽            -> 通栏 table*（IEEE 处理宽表的标准做法）
    w = MEASURED_WIDTHS.get(key)
    if w is None:
        w = _est_width_pt(d)
    wide = w > 1.30 * _COL_PT
    env = 'table*' if wide else 'table'
    avail = r'\textwidth' if wide else r'\columnwidth'

    out = [r'\begin{%s}[!t]' % env, r'\centering',
           _caption(d.get('caption', '')),
           r'\label{tab:%s}' % key,
           size_cmd, r'\setlength{\tabcolsep}{4pt}',
           r'\begin{adjustbox}{max width=%s}' % avail,
           r'\wigmeasure{%s}{%%' % key,
           r'\begin{tabular}{%s}' % colspec, r'\toprule']
    out.append(' & '.join(_cell(h) for h in headers) + r' \\')
    out.append(r'\midrule')
    for r_ in rows:
        out.append(' & '.join(_cell(c) for c in r_) + r' \\')
    out += [r'\bottomrule', r'\end{tabular}}', r'\end{adjustbox}',
            r'\end{%s}' % env, '']
    return '\n'.join(out)


def author_block(name: str, affil: str, email: str, orcid: str = '') -> str:
    """构造 IEEEtran 的 \\author{...} 内容（单一作者、单一单位）。

    返回值会整体替换进 %(authorblock)s，替换后不再经过 % 格式化，
    因此这里可以安全地包含 LaTeX 的 \\\\、% 与 {}。

    name 为空时返回只占位的空作者块——公开仓库版据此去掉全部个人信息，
    但仍让 IEEEtran 保留正常的标题版式。
    """
    if not name:
        return '\n\\IEEEauthorblockN{}\n'
    lines = [
        '',
        r'\IEEEauthorblockN{%s}' % _esc_text(name),
        r'\IEEEauthorblockA{\textit{%s}\\' % _esc_text(affil),
    ]
    if orcid:
        lines.append(r'ORCID: %s\\' % _esc_text(orcid))
    lines.append(r'Corresponding author: %s}' % _esc_text(email))
    lines.append('')
    return '\n'.join(lines)


def render(blocks, out_path, *, title, abstract_text, keywords, refs,
           fig_dir, authorblock=None, bib_items=None):
    body = []
    eq_no = 0
    tab_no = 0
    fig_no = 0

    for kind, payload in blocks:
        if kind == 'h1':
            body.append(r'\section{%s}' % _esc_text(payload))
        elif kind == 'h2':
            # IEEEtran 自动给 \subsection 编号，故去掉内容模型里为 Word 准备的手写字母
            body.append(r'\subsection{%s}' % _esc_text(_strip_letter(payload)))
        elif kind == 'h3':
            body.append(r'\subsubsection{%s}' % _esc_text(payload))
        elif kind == 'p':
            body.append(_esc_text(payload))
            body.append('')
        elif kind == 'bullet':
            body.append(r'\begin{itemize}')
            for it in payload:
                body.append(r'  \item ' + _esc_text(it))
            body.append(r'\end{itemize}')
            body.append('')
        elif kind == 'num':
            body.append(r'\begin{enumerate}')
            for it in payload:
                body.append(r'  \item ' + _esc_text(it))
            body.append(r'\end{enumerate}')
            body.append('')
        elif kind == 'eq':
            latex, number = payload          # 英文版 number 恒为 None：交给 LaTeX 顺序编号
            # 长公式在双栏里会越界压住相邻栏；这里用 adjustbox 的 max width 兜底，
            # 只有在真的超宽时才按比例缩小，短公式不受影响。
            body.append(r'\begin{equation}')
            body.append(r'\adjustbox{max width=\columnwidth}{$\displaystyle %s$}' % latex)
            body.append(r'\end{equation}')
            body.append('')
            eq_no += 1
        elif kind == 'table':
            d = dict(payload)
            tab_no += 1
            d['label'] = f't{tab_no}'
            body.append(_table(d))
        elif kind == 'figure':
            d = dict(payload)
            fig_no += 1
            scale = min(float(d.get('width_cm', 8.0)) / _COL_CM, 1.0)
            body.append(r'\begin{figure}[!t]')
            body.append(r'\centering')
            body.append(r'\includegraphics[width=%.2f\linewidth]{%s}'
                        % (scale, d['name']))
            body.append(r'\vspace{2pt}')
            body.append(_caption(d.get('caption', '')))
            body.append(r'\label{fig:%s}' % d.get('key', 'f%d' % fig_no))
            body.append(r'\end{figure}')
            body.append('')
        elif kind == 'note':
            body.append(r'\begin{quote}\footnotesize ' + _esc_text(payload) + r'\end{quote}')
        elif kind == 'refs':
            body.append(r'\begin{thebibliography}{99}')
            for i, ref in enumerate(payload, 1):
                body.append(r'\bibitem{r%d} %s' % (i, _esc_text(ref)))
            body.append(r'\end{thebibliography}')
            body.append('')
        else:
            raise ValueError(f'未知 IR 块：{kind}')

    head = _PREAMBLE % {
        'title': _esc_text(title),
        'authorblock': authorblock if authorblock else author_block(
            'Author Name', 'Affiliation', 'author@example.com'),
        'abstract': _esc_text(abstract_text),
        'keywords': _esc_text(keywords),
    }
    tex = head + '\n'.join(body) + _POSTAMBLE
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(tex)
    return out_path, {'equations': eq_no, 'tables': tab_no, 'figures': fig_no}

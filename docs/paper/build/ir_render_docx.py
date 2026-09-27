# -*- coding: utf-8 -*-
"""ir_render_docx.py —— 把内容 IR 渲染为中文会议论文 .docx。

IR 块类型：
    ('h1'|'h2'|'h3', text)          章节标题
    ('p', text)                     正文段落（支持 $公式$ 与 **加粗**）
    ('bullet', [items])             无序列表
    ('num', [items])                有序列表
    ('eq', (latex, number))         显示公式，number 为已解析好的打印编号，如 '(9)'
    ('table', {...})                三线表，caption/表头/表体里的交叉引用已解析
    ('figure', {...})               插图，caption 里的交叉引用已解析
    ('note', text)                  小字注
    ('refs', [str])                 参考文献条目

图、表、公式的编号由 build_all.resolve() 在构建时统一分配并写进题注/公式号，
本渲染器只负责排版，不再自行编号。
"""
from __future__ import annotations

import os
import re

from paper_docx import PaperReport

# ------------------------------------------------------------ LaTeX -> 纯文本
_GREEK = {
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε',
    'varepsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'vartheta': 'ϑ',
    'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ',
    'pi': 'π', 'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ',
    'phi': 'φ', 'varphi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
    'Gamma': 'Γ', 'Delta': 'Δ', 'Theta': 'Θ', 'Lambda': 'Λ', 'Xi': 'Ξ',
    'Pi': 'Π', 'Sigma': 'Σ', 'Upsilon': 'Υ', 'Phi': 'Φ', 'Psi': 'Ψ', 'Omega': 'Ω',
}
_SYM = {
    'partial': '∂', 'times': '×', 'cdot': '·', 'pm': '±', 'mp': '∓',
    'leq': '≤', 'le': '≤', 'geq': '≥', 'ge': '≥', 'neq': '≠', 'ne': '≠',
    'approx': '≈', 'equiv': '≡', 'sim': '~', 'propto': '∝', 'infty': '∞',
    'to': '→', 'rightarrow': '→', 'in': '∈', 'forall': '∀', 'exists': '∃',
    'prime': '′', 'degree': '°', 'angle': '∠', 'perp': '⊥', 'nabla': '∇',
    'sum': 'Σ', 'int': '∫', 'sqrt': '√', 'ldots': '…', 'dots': '…',
    'cdots': '⋯', 'vert': '|', 'Vert': '‖', 'lvert': '|', 'rvert': '|',
    'lVert': '‖', 'rVert': '‖', 'quad': ' ', 'qquad': '  ',
}
_SUB = str.maketrans('0123456789+-=()aeoxhklmnpst', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ')
_SUP = str.maketrans('0123456789+-=()n', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ')


def tex_to_plain(s: str) -> str:
    """把 `$...$` 片段转成可在 Word 表格/题注中显示的纯文本（Unicode）。"""
    def one(m: str) -> str:
        t = m
        t = re.sub(r'\\mathrm\{([^{}]*)\}', r'\1', t)
        t = re.sub(r'\\text\{([^{}]*)\}', r'\1', t)
        t = re.sub(r'\\mathbf\{([^{}]*)\}', r'\1', t)
        t = re.sub(r'\\mathcal\{([^{}]*)\}', r'\1', t)
        t = re.sub(r'\\operatorname\{([^{}]*)\}', r'\1', t)
        for k, v in sorted(_SYM.items(), key=lambda kv: -len(kv[0])):
            t = t.replace('\\' + k, v)
        for k, v in sorted(_GREEK.items(), key=lambda kv: -len(kv[0])):
            t = re.sub(r'\\' + k + r'(?![A-Za-z])', v, t)
        t = t.replace('\\,', ' ').replace('\\;', ' ').replace('\\ ', ' ')
        t = t.replace('\\!', '').replace('\\left', '').replace('\\right', '')
        t = t.replace('\\', '')
        # 上下标 -> Unicode
        def sub(mm):
            body = mm.group(1) or mm.group(2)
            return body.translate(_SUB) if all(c in '0123456789+-=()aeoxhklmnpst' for c in body) \
                else '_' + body
        def sup(mm):
            body = mm.group(1) or mm.group(2)
            return body.translate(_SUP) if all(c in '0123456789+-=()n' for c in body) \
                else '^' + body
        t = re.sub(r'_\{([^{}]*)\}|_(\w)', sub, t)
        t = re.sub(r'\^\{([^{}]*)\}|\^(\w)', sup, t)
        return t

    return re.sub(r'\$([^$]*)\$', lambda m: one(m.group(1)), s)


def rich_runs(r: PaperReport, text: str, size_pt: float, base_bold: bool = False) -> str:
    """把含 **加粗** 与 $公式$ 的文本转为一串 run。"""
    out = []
    for i, part in enumerate(text.split('**')):
        if not part:
            continue
        bold = base_bold ^ (i % 2 == 1)
        out.append(r._runs_with_math(part, size_pt, bold=bold))
    return ''.join(out)


# ------------------------------------------------------------ 渲染
def render(blocks, out_path, *, title, authors, affil, abstract_text, keywords,
           clc, fund, en_title, en_abstract, en_keywords, refs,
           fig_dir, body_size=10.5, line_spacing=1.25):
    r = PaperReport(title=title, author=authors, date='',
                    ascii_font='Times New Roman', east_font='宋体',
                    heading_east_font='黑体', accent='000000',
                    body_size_pt=body_size, line_spacing=line_spacing)

    r.paper_title(title)
    # 公开仓库版会传空字符串 / 空列表：此处跳过，避免留下空白作者行
    if authors:
        r.paper_authors(authors)
    if affil:
        r.paper_affil(affil)
    r.abstract(abstract_text)
    r.keywords(keywords)
    r.meta_line(clc)
    r.meta_line(fund)
    r.rule()
    r.en_abstract(en_title, en_abstract, en_keywords)
    r.rule()

    for kind, payload in blocks:
        if kind == 'h1':
            r.h1(payload)
        elif kind == 'h2':
            r.h2(payload)
        elif kind == 'h3':
            r.h3(payload)
        elif kind == 'p':
            xml = rich_runs(r, payload, body_size)
            r._emit(r._para(xml, align='both', first_line=True, after=30), 'p')
        elif kind == 'bullet':
            for it in payload:
                xml = rich_runs(r, it, body_size)
                r._blocks.append(
                    '<w:p><w:pPr>' + r._spacing(0, 0, line=280) +
                    '<w:ind w:left="640" w:hanging="320"/><w:jc w:val="both"/></w:pPr>' +
                    r._run('● ', body_size, east_font='宋体') + xml + '</w:p>')
                r._last_kind = 'bullet'
        elif kind == 'num':
            for i, it in enumerate(payload, 1):
                xml = rich_runs(r, it, body_size)
                r._blocks.append(
                    '<w:p><w:pPr>' + r._spacing(0, 0, line=280) +
                    '<w:ind w:left="640" w:hanging="320"/><w:jc w:val="both"/></w:pPr>' +
                    r._run(f'({i}) ', body_size) + xml + '</w:p>')
                r._last_kind = 'num'
        elif kind == 'eq':
            latex, number = payload
            r.eq(latex, number=number)
        elif kind == 'table':
            d = dict(payload)
            r.table(headers=[tex_to_plain(h) for h in d['headers']],
                    rows=[[tex_to_plain(c) for c in row] for row in d['rows']],
                    caption=tex_to_plain(d.get('caption', '')),
                    widths=d.get('widths'), font_size=d.get('font_size', 9.5),
                    aligns=d.get('aligns'))
        elif kind == 'figure':
            d = dict(payload)
            path = os.path.join(fig_dir, d['name'] + '.png')
            r.figure(path, caption=tex_to_plain(d.get('caption', '')),
                     width_cm=d.get('width_cm', 14.5))
        elif kind == 'note':
            r.note(tex_to_plain(payload))
        elif kind == 'refs':
            for i, ref in enumerate(payload, 1):
                r.ref_item(tex_to_plain(ref) if not ref.startswith('[') else ref)
        else:
            raise ValueError(f'未知 IR 块：{kind}')

    return r.save(out_path), r.warnings

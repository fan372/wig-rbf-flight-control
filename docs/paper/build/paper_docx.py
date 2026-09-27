# -*- coding: utf-8 -*-
"""paper_docx.py —— 中文会议论文专用 .docx 构建器。

复用 `matlab_simulink/tools/word/report_docx.py` 的纯标准库 OOXML 引擎
（zipfile + XML 模板 + OMML 公式），只额外补充会议论文需要的版头：
标题 / 作者 / 单位 / 摘要 / 关键词 / 中图分类号 / 基金项目 / 英文摘要。

不使用 python-docx，输出可直接用 Word 2016+ 打开，无"修复"提示。
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# report_docx.py / omml.py 可能位于若干位置之一：
#   1) 与 paper_docx.py 同目录（仓库 docs/paper/build/ 自带一份拷贝的情况）
#   2) 工作区布局 <root>/conference_paper/tools  ->  <root>/matlab_simulink/tools/word
#   3) 仓库布局   <repo>/docs/paper/build       ->  <repo>/tools/word
_WORD_CANDIDATES = [
    _HERE,
    os.path.abspath(os.path.join(_HERE, '..', '..', 'matlab_simulink', 'tools', 'word')),
    os.path.abspath(os.path.join(_HERE, '..', '..', '..', 'tools', 'word')),
]
for _cand in _WORD_CANDIDATES:
    if os.path.isfile(os.path.join(_cand, 'report_docx.py')):
        if _cand not in sys.path:
            sys.path.insert(0, _cand)
        break
else:
    raise ImportError(
        'paper_docx 需要 report_docx.py（本工程 tools/word 下的纯标准库 .docx 引擎）；'
        '已尝试：' + '; '.join(_WORD_CANDIDATES))

from report_docx import Report, _esc  # noqa: E402


class PaperReport(Report):
    """会议论文构建器：在 Report 之上增加版头与常用排版块。"""

    # ---------------------------------------------------------------
    def _para(self, runs_xml: str, *, align: str = 'both',
              first_line: bool = False, before: int = 0, after: int = 0,
              line: int | None = 360, keep_next: bool = False) -> str:
        ppr = ['<w:pPr>']
        if keep_next:
            ppr.append('<w:keepNext/>')
        if line is None:
            ppr.append(f'<w:spacing w:before="{before}" w:after="{after}"/>')
        else:
            ppr.append(f'<w:spacing w:before="{before}" w:after="{after}" '
                       f'w:line="{line}" w:lineRule="auto"/>')
        if first_line:
            ppr.append('<w:ind w:firstLineChars="200" w:firstLine="480"/>')
        else:
            ppr.append('<w:ind w:firstLine="0" w:firstLineChars="0"/>')
        ppr.append(f'<w:jc w:val="{align}"/>')
        ppr.append('</w:pPr>')
        return '<w:p>' + ''.join(ppr) + runs_xml + '</w:p>'

    # ---------------------------------------------------------------
    def paper_title(self, title: str, *, size_pt: float = 18.0) -> None:
        """论文题目：居中、加粗、黑体。"""
        runs = self._run(title, size_pt, bold=True, east_font='黑体')
        self._emit(self._para(runs, align='center', after=120, line=None), 'title')

    def paper_authors(self, authors: str, *, size_pt: float = 12.0) -> None:
        runs = self._run(authors, size_pt, east_font='仿宋')
        self._emit(self._para(runs, align='center', after=40, line=None), 'author')

    def paper_affil(self, lines, *, size_pt: float = 9.0) -> None:
        if isinstance(lines, str):
            lines = [lines]
        for i, ln in enumerate(lines):
            runs = self._run(ln, size_pt)
            self._emit(self._para(runs, align='center', after=20 if i < len(lines) - 1 else 120,
                                  line=None), 'affil')

    # ---------------------------------------------------------------
    def abstract(self, text: str, *, label: str = '摘\u3000要：',
                 size_pt: float = 10.5) -> None:
        """摘要段落：标签加粗，正文用 $...$ 支持行内公式。"""
        runs = self._run(label, size_pt, bold=True, east_font='黑体')
        runs += self._runs_with_math(text, size_pt)
        self._emit(self._para(runs, align='both', after=60, line=300), 'abstract')

    def keywords(self, text: str, *, label: str = '关键词：',
                 size_pt: float = 10.5) -> None:
        runs = self._run(label, size_pt, bold=True, east_font='黑体')
        runs += self._runs_with_math(text, size_pt)
        self._emit(self._para(runs, align='both', after=60, line=300), 'keywords')

    def meta_line(self, text: str, *, size_pt: float = 10.5) -> None:
        runs = self._runs_with_math(text, size_pt)
        self._emit(self._para(runs, align='left', after=60, line=300), 'meta')

    def rule(self) -> None:
        """一条分隔横线（用段落下边框实现）。"""
        xml = ('<w:p><w:pPr><w:pBdr>'
               '<w:bottom w:val="single" w:sz="6" w:space="1" w:color="808080"/>'
               '</w:pBdr>' + self._spacing(0, 60) +
               '<w:ind w:firstLine="0" w:firstLineChars="0"/></w:pPr></w:p>')
        self._emit(xml, 'rule')

    def en_abstract(self, title_en: str, text_en: str,
                    keywords_en: str, *, size_pt: float = 10.0) -> None:
        """英文题目 / Abstract / Key words（中文会议论文常见版式）。"""
        runs = self._run(title_en, size_pt + 1, bold=True)
        self._emit(self._para(runs, align='center', after=60, line=300), 'entitle')

        runs = self._run('Abstract: ', size_pt, bold=True)
        runs += self._runs_with_math(text_en, size_pt)
        self._emit(self._para(runs, align='both', after=40, line=300), 'enabs')

        runs = self._run('Key words: ', size_pt, bold=True)
        runs += self._runs_with_math(keywords_en, size_pt)
        self._emit(self._para(runs, align='both', after=120, line=300), 'enkw')

    # ---------------------------------------------------------------
    def h1n(self, number: str, text: str) -> None:
        """带章节号的一级标题（如 "1  引言"）。"""
        self.h1(f'{number}  {text}')

    def h2n(self, number: str, text: str) -> None:
        self.h2(f'{number}  {text}')

    def h3n(self, number: str, text: str) -> None:
        self.h3(f'{number}  {text}')

    def ref_item(self, text: str) -> None:
        """参考文献条目：悬挂缩进、小五号。"""
        xml = ('<w:p><w:pPr>' + self._spacing(0, 0, line=260) +
               '<w:ind w:left="480" w:hanging="480"/>'
               '<w:jc w:val="both"/></w:pPr>' +
               self._runs_with_math(text, 9.0) + '</w:p>')
        self._emit(xml, 'ref')

    # ---------------------------------------------------------------
    def page_setup_a4(self) -> None:
        """（占位）版式已在 Report._sectpr 中固定为 A4；此处保留扩展点。"""
        return None

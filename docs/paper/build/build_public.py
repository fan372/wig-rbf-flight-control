# -*- coding: utf-8 -*-
"""build_public.py —— 生成「公开仓库版」论文（完整版，去掉全部作者信息）。

为什么要单独一份：投稿用的 `conference_paper/zh|en/` 带真实署名，
而 GitHub 仓库是公开的，不应附带个人姓名、单位与邮箱。
本脚本复用与投稿版完全相同的内容模型、编号解析与校验逻辑，
只把作者块置空——正文、图、表、公式、参考文献与投稿版逐字一致。

输出到 `conference_paper/public/`：
    wig-rbf-flight-control-paper-zh.docx   中文完整版（无作者）
    wig-rbf-flight-control-paper-en.tex    英文完整版（无作者）
    figures/                               英文标注插图（供 .tex 编译）
中文 docx 之后由 docx2pdf.ps1 转成同名 pdf。

用法：
    python build_public.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_all as BA          # noqa: E402
import content_en              # noqa: E402
import content_zh              # noqa: E402
import ir_render_docx          # noqa: E402
import ir_render_tex           # noqa: E402
import refs as refs_mod        # noqa: E402

PUBLIC = os.path.join(BA.PAPER, 'public')
LEVEL = 12                      # 只出完整版


def main() -> int:
    M = BA.load_metrics()
    os.makedirs(PUBLIC, exist_ok=True)

    figures = os.path.join(PUBLIC, 'figures')
    en_src, have_en = BA.pick_en_figdir()
    if not have_en:
        sys.exit('缺少 matlab_simulink/figures_en/ —— 请先运行 src/run_figs_en.m')
    nfig = BA.copy_figures(figures, en_src)

    # ---------------- 中文 Word（无作者） ----------------
    raw_zh = content_zh.build(LEVEL, M, refs_mod.REFS_ZH)
    blocks_zh = BA.resolve(raw_zh, 'zh', LEVEL)
    BA.check_no_tokens(blocks_zh, 'zh', LEVEL)
    BA.check_contiguous(blocks_zh, 'zh', LEVEL)
    BA.check_section_refs(blocks_zh, 'zh', LEVEL)
    out_zh = os.path.join(PUBLIC, 'wig-rbf-flight-control-paper-zh.docx')
    path_zh, warn = ir_render_docx.render(
        blocks_zh, out_zh,
        title=content_zh.TITLE_ZH,
        authors='',                       # <- 公开版：不署名
        affil=[],                         # <- 公开版：无单位、无邮箱
        abstract_text=content_zh.abstract(M),
        keywords=content_zh.KEYWORDS_ZH,
        clc=content_zh.CLC,
        fund=content_zh.FUND,
        en_title=content_zh.TITLE_EN,
        en_abstract=content_zh.abstract_en(M),
        en_keywords=content_zh.KEYWORDS_EN,
        refs=refs_mod.REFS_ZH,
        fig_dir=BA.FIG_SRC,
        body_size=BA.BODY_SIZE[LEVEL],
        line_spacing=BA.LINE_SPACING[LEVEL],
    )
    if warn:
        print(f'  [警告] {os.path.basename(path_zh)}: {warn}')

    # ---------------- 英文 IEEE LaTeX（无作者） ----------------
    raw_en = content_en.build(LEVEL, M, refs_mod.REFS_EN)
    BA.check_parallel(raw_zh, raw_en, LEVEL)
    blocks_en = BA.resolve(raw_en, 'en', LEVEL)
    BA.check_no_tokens(blocks_en, 'en', LEVEL)
    BA.check_contiguous(blocks_en, 'en', LEVEL)
    BA.check_section_refs(blocks_en, 'en', LEVEL)
    out_tex = os.path.join(PUBLIC, 'wig-rbf-flight-control-paper-en.tex')
    ir_render_tex.render(
        blocks_en, out_tex,
        title=content_en.TITLE_EN,
        authorblock=ir_render_tex.author_block('', '', ''),   # <- 公开版：不署名
        abstract_text=content_en.abstract(M),
        keywords=content_en.KEYWORDS_EN,
        refs=refs_mod.REFS_EN,
        fig_dir=figures,
    )

    print(f'  公开版插图 {nfig} 张 -> {os.path.relpath(figures, BA.ROOT)}')
    print(f'  [公开版] {os.path.relpath(path_zh, BA.ROOT)}')
    print(f'  [公开版] {os.path.relpath(out_tex, BA.ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

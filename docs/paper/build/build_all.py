# -*- coding: utf-8 -*-
"""build_all.py —— 生成中文 Word 与英文 IEEE LaTeX 两套会议论文（各 6/8/12 页版本）。

流程：
    1. extract_metrics.py 解析 results/log_*.txt -> metrics.json（唯一数值来源）
    2. content_zh / content_en 依据 level 选取内容块；图/表/公式只带“短键”，不带编号
    3. resolve() 按文档顺序自动编号，并把 @fig:key@ / @tab:key@ / @eq:key@ 全部替换为数字
    4. ir_render_docx / ir_render_tex 渲染

用法：
    python build_all.py            # 生成全部 6 份正文
    python build_all.py --level 8  # 只生成 8 页版本
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PAPER, '..'))
FIG_SRC = os.path.join(ROOT, 'matlab_simulink', 'figures')
# 英文版用英文标注的图（由 matlab_simulink/src/run_figs_en.m 生成到 figures_en/）。
# 找不到时退回中文图，并在构建报告里明确提示——绝不静默地把中文图塞进英文论文。
FIG_SRC_EN = os.path.join(ROOT, 'matlab_simulink', 'figures_en')

sys.path.insert(0, HERE)

import content_zh  # noqa: E402
import content_en  # noqa: E402
import ir_render_docx  # noqa: E402
import ir_render_tex  # noqa: E402
import refs as refs_mod  # noqa: E402

LEVELS = (6, 8, 12)
# 中文文件名一律带上【实测页数】，避免文件名承诺的页数与实际排版不符：
#   英文 IEEE 双栏 A4 三档恰为 6 / 8 / 11 页，符合 6/8/12 的目标；
#   中文 Word 单栏 A4 在 9.5 pt 字号下、同一套内容约为英文的 1.7 倍长，
#   三档实测为 11 / 14 / 21 页。要压到 6/8/12 就必须删掉论文的技术主体
#   （28 个公式 + 6 张必备表格 + 版头 + 参考文献本身就超过 6 页），故如实标注。
LEVEL_TAG = {6: '压缩版_10页', 8: '标准版_14页', 12: '完整版_21页'}
LEVEL_TAG_EN = {6: '6p-compact', 8: '8p-standard', 12: '12p-extended'}

# 各页数版本的版心排版参数（题注/表格字号在图、表块里单独给）
BODY_SIZE = {6: 9.5, 8: 9.5, 12: 10.0}
LINE_SPACING = {6: 1.05, 8: 1.05, 12: 1.10}

# ---------------------------------------------------------------- 交叉引用解析
_TOKEN_RE = re.compile(r'@(fig|tab|eq):([A-Za-z0-9_]+)@')
_ROMAN = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII',
          'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX')
_KIND_CN = {'fig': '图', 'tab': '表', 'eq': '公式'}
_CAP_NUM_RE = {
    'zh': {'fig': re.compile(r'^图 (\d+)  '), 'tab': re.compile(r'^表 (\d+)  ')},
    'en': {'fig': re.compile(r'^Fig\. (\d+)\. '), 'tab': re.compile(r'^TABLE ([IVXL]+)\. ')},
}


def roman(n: int) -> str:
    """1 -> I, 2 -> II ……"""
    if not 1 <= n <= len(_ROMAN):
        raise ValueError(f'罗马数字超出预置范围：{n}')
    return _ROMAN[n - 1]


def unroman(s: str) -> int:
    """罗马数字转阿拉伯数字（用于编号校验）。"""
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    out = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        out += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return out


def _iter_strings(blocks):
    """遍历 IR 中所有可用于交叉引用的字符串（段落/列表/表头表体/题注/注/参考文献）。"""
    for kind, payload in blocks:
        if kind in ('h1', 'h2', 'h3', 'p', 'note'):
            yield payload
        elif kind in ('bullet', 'num', 'refs'):
            for s in payload:
                yield s
        elif kind == 'eq':
            yield payload[0]
            if payload[1]:
                yield payload[1]
        elif kind in ('figure', 'table'):
            for v in payload.values():
                if isinstance(v, str):
                    yield v
                elif isinstance(v, (list, tuple)):
                    for x in v:
                        if isinstance(x, str):
                            yield x
                        elif isinstance(x, (list, tuple)):
                            yield from (y for y in x if isinstance(y, str))
        else:
            raise ValueError(f'未知 IR 块：{kind}')


def resolve(blocks, lang, level=None):
    """按文档顺序给图/表/公式编号，写入题注，并把 @kind:key@ 全部换成数字。

    lang='zh'：题注 `图 N  …` / `表 N  …`，公式号打印为 `(N)`；
    lang='en'：题注 `Fig. N. …` / `TABLE <罗马数字>. …`，公式交给 LaTeX 自动编号。
    引用了本版本没有收录的块时直接报错，绝不留下未解析的 @…@ 或错误编号。
    """
    if lang not in ('zh', 'en'):
        raise ValueError(f'resolve(): 未知语言 {lang!r}')

    ids = {'fig': {}, 'tab': {}, 'eq': {}}
    titles = {'fig': [], 'tab': [], 'eq': []}
    for kind, payload in blocks:
        if kind == 'figure':
            key = payload.get('key')
            _register(ids, titles, 'fig', key, payload.get('name', ''), lang, level)
        elif kind == 'table':
            key = payload.get('key')
            _register(ids, titles, 'tab', key, payload.get('caption', '')[:20], lang, level)
        elif kind == 'eq':
            _register(ids, titles, 'eq', payload[1], payload[0][:24], lang, level)

    def sub(text):
        def one(m):
            kind, key = m.group(1), m.group(2)
            if key not in ids[kind]:
                raise KeyError(
                    f'[{lang} {level} 页版] 交叉引用 @{kind}:{key}@ 指向的'
                    f'{_KIND_CN[kind]}在本版本中被裁掉；'
                    f'本版本已收录的 {_KIND_CN[kind]}：{sorted(ids[kind])}')
            return _printed(kind, ids[kind][key], lang, plain=True)
        return _TOKEN_RE.sub(one, text)

    out = []
    for kind, payload in blocks:
        if kind in ('h1', 'h2', 'h3', 'p', 'note'):
            out.append((kind, sub(payload)))
        elif kind in ('bullet', 'num', 'refs'):
            out.append((kind, [sub(s) for s in payload]))
        elif kind == 'eq':
            latex, key = payload
            n = ids['eq'][key]
            out.append(('eq', (latex, f'({n})' if lang == 'zh' else None)))
        elif kind == 'figure':
            d = dict(payload)
            n = ids['fig'][d['key']]
            title = sub(d.get('caption', ''))
            d['caption'] = (f'图 {n}  {title}' if lang == 'zh'
                            else f'Fig. {n}. {title}')
            out.append(('figure', d))
        elif kind == 'table':
            d = dict(payload)
            n = ids['tab'][d['key']]
            title = sub(d.get('caption', ''))
            d['caption'] = (f'表 {n}  {title}' if lang == 'zh'
                            else f'TABLE {roman(n)}. {title}')
            d['label'] = d['key']            # LaTeX \label 用稳定的键，不用序号
            out.append(('table', d))
        else:
            raise ValueError(f'未知 IR 块：{kind}')
    return out


def _printed(kind, n, lang, plain=False):
    """引用/题注里出现的编号写法。"""
    if kind == 'tab' and lang == 'en':
        return roman(n)
    return str(n)


def _register(ids, titles, kind, key, hint, lang, level):
    if not key or not isinstance(key, str):
        raise ValueError(
            f'[{lang} {level} 页版] {_KIND_CN[kind]}块缺少稳定 key（{hint!r}）')
    if key in ids[kind]:
        raise ValueError(
            f'[{lang} {level} 页版] {_KIND_CN[kind]} key 重复：{key!r}（{hint!r}）')
    ids[kind][key] = len(titles[kind]) + 1
    titles[kind].append(key)


# ---------------------------------------------------------------- 生成后自检
def check_no_tokens(blocks, lang, level):
    """解析后不允许任何 @…@ 残留。"""
    bad = [s for s in _iter_strings(blocks) if '@' in s]
    if bad:
        raise AssertionError(
            f'[{lang} {level} 页版] 解析后仍残留 @ 标记：{bad[:3]}')


def check_contiguous(blocks, lang, level):
    """图号、表号必须正好是 1..N，且题注里写的就是这个号；公式号同样连续。"""
    exp = {'fig': 0, 'tab': 0, 'eq': 0}
    for kind, payload in blocks:
        if kind == 'figure':
            exp['fig'] += 1
            _check_caption(payload.get('caption', ''), 'fig', exp['fig'], lang, level)
        elif kind == 'table':
            exp['tab'] += 1
            _check_caption(payload.get('caption', ''), 'tab', exp['tab'], lang, level)
        elif kind == 'eq':
            exp['eq'] += 1
            got = payload[1]
            want = f"({exp['eq']})" if lang == 'zh' else None
            if got != want:
                raise AssertionError(
                    f'[{lang} {level} 页版] 第 {exp["eq"]} 个公式的编号为 {got!r}，应为 {want!r}')
    return exp


def _check_caption(caption, kind, n, lang, level):
    m = _CAP_NUM_RE[lang][kind].match(caption)
    if not m:
        raise AssertionError(
            f'[{lang} {level} 页版] {_KIND_CN[kind]}题注缺少 {n} 号：{caption[:40]!r}')
    got = unroman(m.group(1)) if lang == 'en' and kind == 'tab' else int(m.group(1))
    if got != n:
        raise AssertionError(
            f'[{lang} {level} 页版] {_KIND_CN[kind]}题注编号跳号：题目为 {got}，应为 {n}'
            f'（{caption[:40]!r}）')


def section_map(blocks, lang):
    """返回 (一级章节标签集合, 二级章节标签集合)，用于校验正文里的章节交叉引用。

    中文一级为 `3`、二级为 `3.2`；英文一级为罗马数字 `III`、二级为 `III-B`。
    """
    top, subn = set(), set()
    sec = 0
    for kind, payload in blocks:
        if kind == 'h1':
            if lang == 'zh':
                m = re.match(r'^(\d+)\s', payload)
                if m:
                    sec = int(m.group(1))
                    top.add(m.group(1))
                else:
                    sec = 0
            else:
                if payload == 'References' or payload.startswith('Appendix'):
                    sec = 0
                else:
                    sec += 1
                    top.add(roman(sec))
        elif kind == 'h2':
            if lang == 'zh':
                m = re.match(r'^(\d+\.\d+)\s', payload)
                if m:
                    subn.add(m.group(1))
            else:
                m = re.match(r'^([A-Z])\.\s', payload)
                if m and sec:
                    subn.add(f'{sec}-{m.group(1)}')
    return top, subn


_ZH_SEC_REF = re.compile(r'第\s*(\d+(?:\.\d+)?)\s*[章节]|(\d+\.\d+)\s*节')
_EN_SEC_REF = re.compile(r'Section\s+([IVXL]+)(?:-([A-Z]))?')


def check_section_refs(blocks, lang, level):
    """正文里的章节交叉引用必须指向本版本确实收录的章节。"""
    top, subn = section_map(blocks, lang)
    bad = []
    for s in _iter_strings(blocks):
        if lang == 'zh':
            for dotted, plain in _ZH_SEC_REF.findall(s):
                ref = dotted or plain
                if ref not in (subn if '.' in ref else top):
                    bad.append((f'{ref} 节/章', s[:50]))
        else:
            for sec, letter in _EN_SEC_REF.findall(s):
                if sec not in top:
                    bad.append((f'Section {sec}', s[:50]))
                elif letter and f'{unroman(sec)}-{letter}' not in subn:
                    bad.append((f'Section {sec}-{letter}', s[:50]))
    if bad:
        raise AssertionError(
            f'[{lang} {level} 页版] 章节交叉引用失效：{bad[:4]}')


def check_parallel(zh_blocks, en_blocks, level):
    """中英两版必须结构一致：块类型与 key 序列完全相同。"""
    def sig(blocks):
        out = []
        for kind, payload in blocks:
            if kind in ('figure', 'table'):
                out.append((kind, payload['key']))
            elif kind == 'eq':
                out.append((kind, payload[1]))
            else:
                out.append((kind, None))
        return out
    a, b = sig(zh_blocks), sig(en_blocks)
    if a != b:
        diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        raise AssertionError(
            f'[level {level}] 中英两版结构不一致：第 {diff} 块 '
            f'zh={a[diff:diff + 1]} en={b[diff:diff + 1]}')


# ---------------------------------------------------------------- 构建
def load_metrics():
    p = os.path.join(HERE, 'metrics.json')
    if not os.path.isfile(p):
        subprocess.run([sys.executable, os.path.join(HERE, 'extract_metrics.py')], check=True)
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def copy_figures(dst, src=FIG_SRC):
    os.makedirs(dst, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(src)):
        if fn.lower().endswith('.png'):
            shutil.copy2(os.path.join(src, fn), os.path.join(dst, fn))
            n += 1
    return n


def pick_en_figdir():
    """英文版插图来源：优先 figures_en/（英文标注），否则退回 figures/ 并告警。"""
    if os.path.isdir(FIG_SRC_EN) and any(f.lower().endswith('.png')
                                         for f in os.listdir(FIG_SRC_EN)):
        return FIG_SRC_EN, True
    return FIG_SRC, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', type=int, choices=LEVELS, default=None)
    args = ap.parse_args()

    M = load_metrics()
    levels = [args.level] if args.level else list(LEVELS)

    en_dir = os.path.join(PAPER, 'en')
    zh_dir = os.path.join(PAPER, 'zh')
    fig_dst = os.path.join(en_dir, 'figures')
    os.makedirs(en_dir, exist_ok=True)
    os.makedirs(zh_dir, exist_ok=True)

    en_src, have_en = pick_en_figdir()
    if not have_en:
        print('  [警告] 未找到 matlab_simulink/figures_en/ —— 英文论文将使用中文标注的插图。\n'
              '         请先运行 src/run_figs_en.m 生成英文图。')
    nfig = copy_figures(fig_dst, en_src)

    report = []
    for lv in levels:
        # ---------------- 中文 Word ----------------
        raw_zh = content_zh.build(lv, M, refs_mod.REFS_ZH)
        blocks_zh = resolve(raw_zh, 'zh', lv)
        check_no_tokens(blocks_zh, 'zh', lv)
        n_zh = check_contiguous(blocks_zh, 'zh', lv)
        check_section_refs(blocks_zh, 'zh', lv)
        out_zh = os.path.join(zh_dir, f'地效飞行器RBF自适应飞控_会议论文_{LEVEL_TAG[lv]}.docx')
        path_zh, warn = ir_render_docx.render(
            blocks_zh, out_zh,
            title=content_zh.TITLE_ZH,
            authors=content_zh.AUTHORS,
            affil=content_zh.AFFIL,
            abstract_text=content_zh.abstract(M),
            keywords=content_zh.KEYWORDS_ZH,
            clc=content_zh.CLC,
            fund=content_zh.FUND,
            en_title=content_zh.TITLE_EN,
            en_abstract=content_zh.abstract_en(M),
            en_keywords=content_zh.KEYWORDS_EN,
            refs=refs_mod.REFS_ZH,
            fig_dir=FIG_SRC,
            body_size=BODY_SIZE[lv],
            line_spacing=LINE_SPACING[lv],
        )
        report.append(('zh', lv, path_zh, len(blocks_zh), n_zh, len(warn)))
        if warn:
            print(f'  [警告] {os.path.basename(path_zh)}: {warn}')

        # ---------------- 英文 IEEE LaTeX ----------------
        raw_en = content_en.build(lv, M, refs_mod.REFS_EN)
        check_parallel(raw_zh, raw_en, lv)
        blocks_en = resolve(raw_en, 'en', lv)
        check_no_tokens(blocks_en, 'en', lv)
        n_en = check_contiguous(blocks_en, 'en', lv)
        check_section_refs(blocks_en, 'en', lv)
        out_tex = os.path.join(en_dir, f'wig_rbf_ieee_{LEVEL_TAG_EN[lv]}.tex')
        path_tex, stats = ir_render_tex.render(
            blocks_en, out_tex,
            title=content_en.TITLE_EN,
            # 作者信息单一事实来源：content_zh 里的 AUTHOR_EN / AFFIL_EN / EMAIL
            authorblock=ir_render_tex.author_block(
                content_zh.AUTHOR_EN, content_zh.AFFIL_EN, content_zh.EMAIL),
            abstract_text=content_en.abstract(M),
            keywords=content_en.KEYWORDS_EN,
            refs=refs_mod.REFS_EN,
            fig_dir=fig_dst,
        )
        report.append(('en', lv, path_tex, len(blocks_en), n_en, stats))

    print(f'\n复制插图 {nfig} 张 -> {fig_dst}')
    print('\n生成结果（图/表/公式编号已按本版本自动连续编号，交叉引用无残留标记）：')
    for lang, lv, path, nblk, n, extra in report:
        print(f'  [{lang}] {lv:>2} 页  {nblk:>3} 块  '
              f'图 {n["fig"]:>2} / 表 {n["tab"]:>2} / 公式 {n["eq"]:>2}  '
              f'{os.path.relpath(path, ROOT)}  {extra}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

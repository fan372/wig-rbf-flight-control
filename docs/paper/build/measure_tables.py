# -*- coding: utf-8 -*-
"""measure_tables.py —— 实测每张表的自然宽度，回填 table_widths.json。

为什么要实测：靠字符数估算 LaTeX 表格宽度不可靠（数学符号、列间距、字体度量
都会影响结果），而"猜错了"的后果很严重——猜小了下场是表格越界压住正文，
猜大了就是通栏表把页数顶上去。

做法：ir_render_tex 会把每个 tabular 包进 \\wigmeasure{key}{...}，编译时该宏把
真实宽度写进 .log（`WIGTABLEWIDTH <key> = <dimen>`）。本脚本编译三份 tex、
解析全部宽度、写成 table_widths.json，之后 build_all 就按实测值排版。

用法：
    python measure_tables.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EN = os.path.abspath(os.path.join(HERE, '..', 'en'))
OUT = os.path.join(HERE, 'table_widths.json')
TEXS = ['wig_rbf_ieee_6p-compact', 'wig_rbf_ieee_8p-standard', 'wig_rbf_ieee_12p-extended']


def find_pdflatex() -> str:
    """定位 pdflatex：优先 PATH，其次环境变量 WIG_PDFLATEX，最后常见安装目录。

    本脚本是可移植的构建工具，不能把某一台机器的 TeX 安装路径写死。
    """
    exe = shutil.which('pdflatex')
    if exe:
        return exe
    env = os.environ.get('WIG_PDFLATEX')
    if env and os.path.isfile(env):
        return env
    for cand in (
        r'C:\texlive\2026\bin\windows\pdflatex.exe',
        r'C:\texlive\2025\bin\windows\pdflatex.exe',
        r'C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe',
        os.path.expanduser(r'~\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'),
    ):
        if os.path.isfile(cand):
            return cand
    sys.exit('找不到 pdflatex。请把它加入 PATH，或用环境变量 WIG_PDFLATEX 指定完整路径。')

_DIM = re.compile(r'WIGTABLEWIDTH\s+(\S+)\s*=\s*([\d.]+)pt')


def compile_one(base: str) -> dict:
    """编译一份 tex，返回 {key: 宽度 pt}。"""
    pdflatex = find_pdflatex()
    for _ in range(2):                     # 两遍，保证交叉引用稳定
        subprocess.run([pdflatex, '-interaction=nonstopmode', base + '.tex'],
                       cwd=EN, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log = os.path.join(EN, base + '.log')
    with open(log, 'r', encoding='utf-8', errors='ignore') as fh:
        txt = fh.read()
    found = {}
    for m in _DIM.finditer(txt):
        found[m.group(1)] = float(m.group(2))
    return found


def main() -> int:
    widths: dict[str, float] = {}
    for base in TEXS:
        tex = os.path.join(EN, base + '.tex')
        if not os.path.isfile(tex):
            print(f'  [跳过] 缺少 {base}.tex')
            continue
        got = compile_one(base)
        print(f'  {base}: 实测到 {len(got)} 张表')
        for k, v in got.items():
            if k in widths and abs(widths[k] - v) > 0.01:
                print(f'    [注意] {k} 在不同版本中宽度不同：{widths[k]:.2f} vs {v:.2f}')
            widths[k] = max(widths.get(k, 0.0), v)

    if not widths:
        sys.exit('没有解析到任何表格宽度——请确认 ir_render_tex 已输出 \\wigmeasure')

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(widths, fh, ensure_ascii=False, indent=1, sort_keys=True)

    col = 252.0
    print(f'\n写出 {OUT}（{len(widths)} 张表；单栏宽 {col:.0f} pt）')
    for k in sorted(widths):
        w = widths[k]
        if w <= 0.95 * col:
            how = '单栏'
        elif w <= 1.30 * col:
            how = f'单栏+缩放 x{col / w:.2f}'
        else:
            how = f'通栏 table*  x{2.05 * col / w:.2f}'
        print(f'  {k:10s} {w:7.2f} pt   {how}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""check_docx_layout.py —— 用 OOXML 实测 Word 文档是否有越界风险。

Word 里正文会自动换行，所以"文字压住文字"不会发生；真正的越界风险只有两类：
  1. 表格总宽 > 版心宽（8730 twips = 15.397 cm）—— 表格会伸到页边距外；
  2. 插图宽 > 版心宽 —— 图片会被裁掉。
此外检查每个表格的列宽之和与表宽声明是否自洽。

用法：
    python check_docx_layout.py <文件或目录> [...]
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

TEXT_W_TW = 8730          # A4 - 左右各 1588 twips
EMU_PER_TWIP = 635
# 表格宽度允许的舍入容差：Word 的 twips 无法精确表示 cm，方程编号用的隐形表格
# 会比版心宽 2 twips（= 0.0035 mm），肉眼与打印都不可能看出来，故不算越界。
TWIP_TOL = 4
W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WP_NS = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'


def check(path: str) -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(path) as z:
        doc = z.read('word/document.xml').decode('utf-8')

    # ---- 1. 表格宽度 ----
    for ti, tbl in enumerate(re.findall(r'<w:tbl>.*?</w:tbl>', doc, re.S), 1):
        m = re.search(r'<w:tblW w:w="(\d+)" w:type="(\w+)"', tbl)
        tblw = int(m.group(1)) if m else None
        ttype = m.group(2) if m else 'auto'
        cols = [int(x) for x in re.findall(r'<w:gridCol w:w="(\d+)"', tbl)]
        grid = sum(cols)
        # 单元格宽度之和（含 gridSpan 的 tcW）
        cellw = [int(x) for x in re.findall(r'<w:tcW w:w="(\d+)" w:type="dxa"', tbl)]
        widest = max(grid, tblw or 0)
        if widest > TEXT_W_TW + TWIP_TOL:
            problems.append(
                f'表 {ti}: 声明宽度 {widest} twips > 版心 {TEXT_W_TW} twips '
                f'（超出 {(widest - TEXT_W_TW) / 567:.2f} cm）')
        if cols and abs(grid - (tblw or grid)) > 2:
            problems.append(f'表 {ti}: 列宽之和 {grid} 与表宽 {tblw} 不一致')
        if ttype == 'pct' and tblw and tblw > 5000:
            problems.append(f'表 {ti}: 百分比宽度异常 {tblw}')

    # ---- 2. 插图宽度 ----
    for ii, cx in enumerate(re.findall(r'<wp:extent cx="(\d+)"', doc), 1):
        tw = int(cx) / EMU_PER_TWIP
        if tw > TEXT_W_TW + 1:
            problems.append(
                f'图 {ii}: 宽度 {tw:.0f} twips > 版心 {TEXT_W_TW} twips '
                f'（超出 {(tw - TEXT_W_TW) / 567:.2f} cm）')

    return problems


def main(argv: list[str]) -> int:
    targets: list[str] = []
    for a in argv:
        if os.path.isdir(a):
            targets += [os.path.join(a, f) for f in sorted(os.listdir(a))
                        if f.lower().endswith('.docx') and not f.startswith('~$')]
        else:
            targets.append(a)

    bad = 0
    for p in targets:
        probs = check(p)
        name = os.path.basename(p)
        if probs:
            bad += 1
            print(f'[越界] {name}')
            for x in probs[:12]:
                print('        ' + x)
            if len(probs) > 12:
                print(f'        …另有 {len(probs) - 12} 条')
        else:
            print(f'[OK]  {name}')
    print(f'\n检查 {len(targets)} 个 .docx，其中 {bad} 个存在越界风险')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

# -*- coding: utf-8 -*-
"""检查 Markdown 正文里有没有"字体画不出来"的字符。

两类问题会被抓出来：
  1. cmap 里根本没有这个码位        -> 一定会丢字
  2. cmap 有、但字形轮廓为空（空白字形）-> 会静默变成空格，最难发现

用法：
    python check_glyphs_pdf.py
报告写到 _glyph_report.txt（UTF-8，Windows 控制台编码不足以显示）。
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(ROOT, 'docs', 'tutorial_src')

from _pdf_gen import TTFont                        # noqa: E402

FONTS = [
    ('中文正文 微软雅黑', r'C:\Windows\Fonts\msyh.ttc'),
    ('中文粗体 微软雅黑', r'C:\Windows\Fonts\msyhbd.ttc'),
    ('西文 Calibri', r'C:\Windows\Fonts\calibri.ttf'),
    ('西文 Calibri Bold', r'C:\Windows\Fonts\calibrib.ttf'),
]
BLANK_OK = {0x20, 0xA0, 0x3000, 0x09, 0x0A, 0x0D}


def main():
    files = sorted(glob.glob(os.path.join(SRC, '*.md')))
    if not files:
        print('找不到 Markdown 源:', SRC)
        return 1

    lines = []
    ok = True
    for label, path in FONTS:
        if not os.path.exists(path):
            lines.append('%s: 字体文件不存在 %s' % (label, path))
            ok = False
            continue
        font = TTFont(path)
        cmap = font.cmap_mapping()
        absent, blank = [], []
        seen = set()
        for fp in files:
            text = open(fp, encoding='utf-8').read()
            for ch in text:
                if ord(ch) < 128 or ch in seen:
                    continue
                seen.add(ch)
                gid = cmap.get(ord(ch))
                if gid is None:
                    absent.append(ch)
                elif len(font.glyph_data(gid)) == 0 and ord(ch) not in BLANK_OK:
                    blank.append(ch)
        lines.append('%s  (%s)' % (label, os.path.basename(path)))
        lines.append('  码位总数  : %d' % len(seen))
        lines.append('  cmap 缺失 : %s' % (''.join(sorted(absent)) or '(无)'))
        lines.append('  空白字形  : %s' % (''.join(sorted(blank)) or '(无)'))
        # 中文正文与粗体必须能画全部中文；西文只要求 ASCII + 中文标点
        if '雅黑' in label and (absent or blank):
            ok = False
        lines.append('')

    lines.append('结论: %s' % ('PASS —— 全部字符都有字形，PDF 不会丢字' if ok else
                              'FAIL —— 存在缺字，见上'))
    txt = '\n'.join(lines) + '\n'
    out = os.path.join(HERE, '_glyph_report.txt')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(txt)
    sys.stdout.buffer.write(txt.encode('utf-8', 'replace'))
    print('report ->', out)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

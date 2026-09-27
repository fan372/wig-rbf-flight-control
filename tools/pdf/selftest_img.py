# -*- coding: utf-8 -*-
"""自检：PNG 解码 + 图片 XObject 嵌入。

用法： python selftest_img.py
产物： _selftest_img.pdf（2 页，含 1 张 MATLAB 导出图与 1 张纯色测试图）
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pdfimg import decode_png, PDFDocImg            # noqa: E402
from _render_pdf import (make_fonts, Measure, Cursor,  # noqa: E402
                         PAGE_H, MARGIN, COL_BLACK, COL_ACCENT,
                         LATIN_REG, LATIN_BOLD, CJK_REG, CJK_BOLD)

FIG = os.path.abspath(os.path.join(HERE, '..', '..', 'figures'))


def make_test_png(path, w=64, h=40):
    """纯 stdlib 生成一张测试 PNG（左红右蓝渐变）。"""
    raw = bytearray()
    for y in range(h):
        raw.append(0)                      # filter = None
        for x in range(w):
            raw += bytes((int(255 * x / (w - 1)), 60, int(255 * (1 - x / (w - 1)))))
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as fh:
        fh.write(png)
    return path


def main():
    ok = True

    # ---- 1. 纯 stdlib 生成的 PNG 往返 ----
    tp = os.path.join(HERE, '_test_grad.png')
    make_test_png(tp)
    w, h, rgb = decode_png(tp)
    print('测试图解码: %dx%d, RGB 字节 %d (期望 %d)' % (w, h, len(rgb), w * h * 3))
    if (w, h) != (64, 40) or len(rgb) != 64 * 40 * 3:
        ok = False
    # 首像素应为 (0,60,255)，尾像素应为 (255,60,0)
    if rgb[0:3] != bytes((0, 60, 255)):
        print('  首像素错误:', rgb[0:3]); ok = False
    if rgb[-3:] != bytes((255, 60, 0)):
        print('  尾像素错误:', rgb[-3:]); ok = False

    # ---- 2. MATLAB 导出图解码 ----
    figs = []
    for nm in ['fig1_ge', 'fig3_modes', 'fig4_tracking']:
        p = os.path.join(FIG, nm + '.png')
        if os.path.exists(p):
            fw, fh, frgb = decode_png(p)
            print('%s: %dx%d, %.1f KB -> RGB %.1f KB'
                  % (nm, fw, fh, os.path.getsize(p) / 1024.0, len(frgb) / 1024.0))
            figs.append((nm, p, fw, fh))
        else:
            print('缺少图片:', p); ok = False

    # ---- 3. 生成 PDF ----
    texts = set('自检报告：图片 XObject 嵌入测试 abcXYZ0123456789 地效飞行器'
                '·—…、。（）%s' % ' '.join(n for n, *_ in figs))
    m = Measure(make_fonts(texts))
    pf = m.pf
    doc = PDFDocImg().enable_tounicode()
    for tag in (LATIN_REG, LATIN_BOLD, CJK_REG, CJK_BOLD):
        doc.add_font(pf[tag])

    cur = Cursor(m, line_ratio=1.4)
    cur._last_size = 14
    cur.emit_text('图片嵌入自检', 14, MARGIN, cur.baseline, COL_ACCENT, True)
    cur.y -= 14 * 1.4 + 12

    for nm, path, fw, fh in figs:
        disp_w = 420.0
        disp_h = disp_w * fh / fw
        if cur.y - disp_h < MARGIN:
            cur.new_page()
        name, iw, ih = doc.add_image(path)
        top = cur.y
        cur.page_items.append(('image', name, MARGIN, top - disp_h, disp_w, disp_h))
        cur.y = top - disp_h - 10
        cur.emit_text(nm, 9, MARGIN, cur.y, COL_BLACK)
        cur.y -= 24

    nm, iw, ih = doc.add_image(tp)
    cur.page_items.append(('image', nm, MARGIN, cur.y - 60, 200.0, 60.0))

    if cur.page_items:
        cur.pages.append(cur.page_items)
    for items in cur.pages:
        doc.add_page(items)

    out = os.path.join(HERE, '_selftest_img.pdf')
    data = doc.serialize()
    with open(out, 'wb') as fh:
        fh.write(data)

    # ---- 4. 结构校验 ----
    nimg = data.count(b'/Type /XObject /Subtype /Image')
    nres = data.count(b'/XObject << /Im')
    print('PDF: %d 字节, %d 页, %d 个图片 XObject, %d 页带图片资源'
          % (len(data), len(cur.pages), nimg, nres))
    if nimg != len(figs) + 1:
        print('  图片对象数不符（期望 %d）' % (len(figs) + 1)); ok = False
    if nres != len(cur.pages):
        print('  带图片资源的页数不符（期望 %d）' % len(cur.pages)); ok = False
    for nm, _p, _w, _h in figs:
        if ('/%s ' % nm).encode() in data:
            print('  资源名异常：不应出现图片文件名'); ok = False
    if not data.startswith(b'%PDF-1.5') or not data.rstrip().endswith(b'%%EOF'):
        print('  PDF 头尾异常'); ok = False

    os.remove(tp)
    print('\nSELFTEST %s -> %s' % ('PASS' if ok else 'FAIL', out))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

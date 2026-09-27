# -*- coding: utf-8 -*-
"""校验生成的 PDF：页数、文字是否越界、字体是否内嵌、缺字审计、可检索性。

用法：
    python verify_pdf.py [pdf路径]
默认校验 md2pdf_tut.py 的输出。报告写到 _verify_pdf.txt（UTF-8）。
"""
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

from _render_pdf import PAGE_W, PAGE_H, MARGIN   # noqa: E402

DEFAULT_PDF = os.path.join(ROOT, 'docs', '地效飞行器自适应飞控_零基础详解.pdf')
REPORT = os.path.join(HERE, '_verify_pdf.txt')


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    L = []
    ok = True

    if not os.path.exists(pdf):
        print('找不到 PDF:', pdf)
        return 1
    data = open(pdf, 'rb').read()
    L.append('文件: %s' % os.path.basename(pdf))
    L.append('大小: %d 字节 (%.2f MB)' % (len(data), len(data) / 1048576.0))

    # ---- 1. 头尾与结构 ----
    if not data.startswith(b'%PDF-'):
        L.append('✗ 缺少 PDF 头'); ok = False
    if not data.rstrip().endswith(b'%%EOF'):
        L.append('✗ 缺少 %%EOF'); ok = False
    npage = len(re.findall(rb'/Type\s*/Page[^s]', data))
    L.append('页数: %d' % npage)
    nfont = len(re.findall(rb'/Type\s*/Font', data))
    ncid = len(re.findall(rb'/Subtype\s*/CIDFontType2', data))
    nfile = len(re.findall(rb'/FontFile2', data))
    L.append('字体: Font 对象 %d, CIDFontType2 %d, 内嵌字体流 FontFile2 %d' % (nfont, ncid, nfile))
    if nfile < 4:
        L.append('✗ 内嵌字体流少于 4 个（应有 4 个中英文字体）'); ok = False
    else:
        L.append('✓ 4 个字体全部内嵌（不会乱码）')

    ntu = len(re.findall(rb'/ToUnicode', data))
    L.append('ToUnicode CMap: %d 个（文字可复制/可检索）' % ntu)
    if ntu < 4:
        L.append('✗ ToUnicode 少于 4 个'); ok = False

    nimg = len(re.findall(rb'/Type\s*/XObject\s*/Subtype\s*/Image', data))
    L.append('嵌入图片: %d 张' % nimg)

    nout = len(re.findall(rb'/Type\s*/Outlines', data))
    nitem = len(re.findall(rb'/Dest\s*\[', data))
    L.append('书签大纲: %s（%d 个跳转目标）' % ('有' if nout else '无', nitem))

    # ---- 2. 解压内容流，检查坐标越界 ----
    over = []
    total_ops = 0
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        blob = data[start:end]
        try:
            txt = zlib.decompress(blob).decode('latin-1')
        except Exception:
            continue
        if 'Tm' not in txt and ' cm ' not in txt:
            continue
        total_ops += txt.count('Tm')
        for tm in re.finditer(r'1 0 0 1 ([\d.\-]+) ([\d.\-]+) Tm', txt):
            x, y = float(tm.group(1)), float(tm.group(2))
            if x < MARGIN - 40 or x > PAGE_W - MARGIN + 40:
                over.append(('文本横坐标越界', x, y))
            if y < MARGIN - 40 or y > PAGE_H - MARGIN + 40:
                over.append(('文本纵坐标越界', x, y))
        for cm in re.finditer(r'q ([\d.\-]+) 0 0 ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) cm', txt):
            w, h, x, y = (float(cm.group(i)) for i in (1, 2, 3, 4))
            if x < MARGIN - 2 or y < MARGIN - 2 or x + w > PAGE_W - MARGIN + 2 \
                    or y + h > PAGE_H - MARGIN + 2:
                over.append(('图片越界', round(x), round(y)))
    L.append('文本定位指令: %d 条' % total_ops)
    if over:
        L.append('✗ 发现 %d 处越界:' % len(over))
        for o in over[:10]:
            L.append('    %s at %s' % (o[0], o[1:]))
        ok = False
    else:
        L.append('✓ 全部文字与图片在版心内，无越界')

    # ---- 3. 缺字审计：把内容流里的 CID 还原成 Unicode，检查是否有 .notdef ----
    touni = {}
    for m in re.finditer(rb'/ToUnicode (\d+) 0 R', data):
        pass
    # 逐个解压 ToUnicode CMap 对象，收集所有映射到的 Unicode
    ncmap = 0
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        try:
            txt = zlib.decompress(data[start:end]).decode('latin-1')
        except Exception:
            continue
        if 'beginbfchar' in txt or 'beginbfrange' in txt:
            ncmap += 1
            for bf in re.finditer(r'<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]{4,})>', txt):
                touni[int(bf.group(1), 16)] = int(bf.group(2)[:4], 16)
    L.append('ToUnicode 映射条目: %d 条（来自 %d 个 CMap）' % (len(touni), ncmap))
    if not touni:
        L.append('✗ 未能解析出 ToUnicode 映射'); ok = False

    # 内容流里 <...> Tj 的 CID，逐个查映射
    missing = set()
    checked = 0
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        try:
            txt = zlib.decompress(data[start:end]).decode('latin-1')
        except Exception:
            continue
        if 'Tj' not in txt or 'Tm' not in txt:
            continue
        for tj in re.finditer(r'<([0-9A-Fa-f]+)>\s*Tj', txt):
            hx = tj.group(1)
            for i in range(0, len(hx) - 3, 4):
                cid = int(hx[i:i + 4], 16)
                checked += 1
                if cid not in touni and cid > 0:
                    missing.add(cid)
    L.append('已排版字符（CID）总数: %d' % checked)
    if missing:
        sample = ''.join(chr(c) for c in sorted(missing)[:40] if 32 <= c < 0x3000)
        L.append('✗ 有 %d 个 CID 没有 ToUnicode 映射（复制时会丢字），样例: %s'
                 % (len(missing), sample))
        ok = False
    else:
        L.append('✓ 所有字符都有 Unicode 映射，全文可复制可检索')

    L.append('')
    L.append('结论: %s' % ('PASS' if ok else 'FAIL'))
    txt = '\n'.join(L) + '\n'
    with open(REPORT, 'w', encoding='utf-8') as fh:
        fh.write(txt)
    sys.stdout.buffer.write(txt.encode('utf-8', 'replace'))
    print('report ->', REPORT)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

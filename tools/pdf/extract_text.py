# -*- coding: utf-8 -*-
"""按字体分别映射，正确提取本工具链生成 PDF 的文字。

关键点：PDF 里有 4 个字体（F1 西文、F2 西文粗、F3 中文、F4 中文粗），
它们各自的 CID 编号是独立的。如果像常见做法那样把所有 ToUnicode 映射
合并成一张表，就会因为 CID 冲突而解出错字——这是"校验脚本自身的 bug"，
不是 PDF 的问题。

用法：
    python extract_text.py [pdf路径] [输出txt路径]
"""
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DEFAULT_PDF = os.path.join(ROOT, 'docs', '地效飞行器自适应飞控_零基础详解.pdf')


def decompress_streams(data):
    """返回 {对象号: 解压后的字节}，对象号来自 'N 0 obj ... stream ... endstream'。"""
    out = {}
    for m in re.finditer(rb'(\d+)\s+0\s+obj\b', data):
        num = int(m.group(1))
        s = data.find(b'stream', m.end())
        if s < 0:
            continue
        e = data.find(b'endstream', s)
        if e < 0:
            continue
        blob = data[s + 6:e]
        blob = blob.lstrip(b'\r\n')
        try:
            out[num] = zlib.decompress(blob)
        except Exception:
            out[num] = blob
    return out


def parse_cmap(txt):
    """解析 ToUnicode CMap，返回 {cid: unicode_int}"""
    mp = {}
    for blk in re.findall(rb'beginbfchar(.*?)endbfchar', txt, re.S):
        for a, b in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            mp[int(a, 16)] = int(b[:4], 16)
    for blk in re.findall(rb'beginbfrange(.*?)endbfrange', txt, re.S):
        for a, b, c in re.findall(
                rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            lo, hi, dst = int(a, 16), int(b, 16), int(c, 16)
            for i in range(hi - lo + 1):
                mp[lo + i] = dst + i
    return mp


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    outp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '_extracted.txt')
    data = open(pdf, 'rb').read()
    objs = decompress_streams(data)

    # 1) 页面资源里的字体名 -> 字体对象号
    fname2obj = {}
    for m in re.finditer(rb'/Font\s*<<([^>]*)>>', data):
        for nm, num in re.findall(rb'/(F\d+)\s+(\d+)\s+0\s+R', m.group(1)):
            fname2obj[nm.decode()] = int(num)
    # 2) 字体对象号 -> ToUnicode 对象号
    fobj2cmap = {}
    for fname, onum in fname2obj.items():
        mm = re.search(rb'%d\s+0\s+obj(.{0,600}?)endobj' % onum, data, re.S)
        if not mm:
            continue
        tu = re.search(rb'/ToUnicode\s+(\d+)\s+0\s+R', mm.group(1))
        if tu:
            fobj2cmap[fname] = int(tu.group(1))
    # 3) 解析各字体的 CMap
    fonts = {}
    for fname, cnum in fobj2cmap.items():
        if cnum in objs:
            fonts[fname] = parse_cmap(objs[cnum])

    # 4) 按 /Type /Page 的出现顺序取出各自的 /Contents 流，逐页提取
    page_contents = []
    for m in re.finditer(rb'/Type\s*/Page[^s]', data):
        seg = data[m.end():m.end() + 400]
        c = re.search(rb'/Contents\s+(\d+)\s+0\s+R', seg)
        if c:
            page_contents.append(int(c.group(1)))

    pages, unknown = [], 0
    for cnum in page_contents:
        if cnum not in objs:
            pages.append('')
            continue
        t = objs[cnum].decode('latin-1', 'replace')
        buf = []
        cur = None
        for tok in re.finditer(r'/(F\d+)\s+[\d.]+\s+Tf|<([0-9A-Fa-f]+)>\s*Tj', t):
            if tok.group(1):
                cur = tok.group(1)
                continue
            hx = tok.group(2)
            mp = fonts.get(cur, {})
            for i in range(0, len(hx) - 3, 4):
                cid = int(hx[i:i + 4], 16)
                ch = mp.get(cid)
                if ch is None:
                    unknown += 1
                    buf.append('\uFFFD')
                else:
                    buf.append(chr(ch))
        pages.append(''.join(buf))

    txt = ('\n\n' + '=' * 30 + ' 分页 ' + '=' * 30 + '\n\n').join(
        '----- 第 %d 页 -----\n%s' % (i + 1, p) for i, p in enumerate(pages))
    with open(outp, 'w', encoding='utf-8') as fh:
        fh.write(txt)

    print('内容流页数: %d' % len(pages))
    print('字体: %s' % ', '.join('%s->%d 条映射' % (k, len(v)) for k, v in sorted(fonts.items())))
    print('无法还原的字符数: %d' % unknown)
    print('提取文本 ->', outp)
    return 0 if unknown == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

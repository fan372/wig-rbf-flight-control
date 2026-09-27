# -*- coding: utf-8 -*-
"""在作者自己早先编写的第一方纯 stdlib PDF 引擎（同目录 _pdf_gen.py）上
【扩展图片支持】。

原引擎只支持文字与矩形，无法插图。
本模块以【子类 + 覆写】的方式扩展，不改动原文件：

    decode_png(path)      -> (w, h, rgb_bytes)
        纯 stdlib PNG 解码（zlib + 逐行反滤波）。支持 8 位、非隔行、
        色彩类型 0/2/3/4/6；带 alpha 的按白底合成。

    PDFDocImg(PDFDoc)     -> 在页面项中新增 ('image', name, x, y, w, h)
        y 为图片【底边】坐标（PDF 坐标原点在左下角，与 Cursor 的 y 一致）。

用法：
    import pdfimg
    doc = pdfimg.PDFDocImg().enable_tounicode()
    name, w, h = doc.add_image('fig1.png')
    doc.add_page([..., ('image', name, 42.5, 300.0, 400.0, 200.0)])
    open('out.pdf','wb').write(doc.serialize())
"""
import os
import struct
import zlib

from _pdf_gen import PDFDoc, _tounicode_cmap  # noqa: F401

__all__ = ['decode_png', 'PDFDocImg']


# ------------------------------------------------------------------ PNG
def _paeth(a, b, c):
    p = a + b - c
    pa = p - a
    if pa < 0:
        pa = -pa
    pb = p - b
    if pb < 0:
        pb = -pb
    pc = p - c
    if pc < 0:
        pc = -pc
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png(path):
    """纯 stdlib 解码 PNG，返回 (宽, 高, RGB 字节串)。"""
    with open(path, 'rb') as fh:
        data = fh.read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('不是 PNG 文件: %s' % path)

    pos = 8
    idat = []
    plte = None
    w = h = bitdepth = colortype = interlace = None
    while pos + 8 <= len(data):
        (length,) = struct.unpack('>I', data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b'IHDR':
            w, h, bitdepth, colortype, _comp, _filt, interlace = struct.unpack(
                '>IIBBBBB', chunk)
        elif ctype == b'PLTE':
            plte = chunk
        elif ctype == b'IDAT':
            idat.append(chunk)
        elif ctype == b'IEND':
            break

    if bitdepth != 8:
        raise ValueError('%s: 仅支持 8 位色深，实际 %d' % (path, bitdepth))
    if interlace != 0:
        raise ValueError('%s: 不支持隔行扫描 PNG' % path)

    raw = zlib.decompress(b''.join(idat))
    nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
    stride = w * nch
    out = bytearray(h * stride)
    prev = bytes(stride)
    p = 0
    for y in range(h):
        f = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if f == 0:
            pass
        elif f == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(nch):
                line[i] = (line[i] + (prev[i] >> 1)) & 0xFF
            for i in range(nch, stride):
                line[i] = (line[i] + ((line[i - nch] + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(nch):
                line[i] = (line[i] + prev[i]) & 0xFF
            for i in range(nch, stride):
                line[i] = (line[i] + _paeth(line[i - nch], prev[i],
                                            prev[i - nch])) & 0xFF
        else:
            raise ValueError('%s: 未知行滤波类型 %d' % (path, f))
        out[y * stride:(y + 1) * stride] = line
        prev = bytes(line)

    rgb = bytearray(w * h * 3)
    if colortype == 2:
        rgb[:] = out
    elif colortype == 0:
        for i in range(w * h):
            g = out[i]
            rgb[3 * i] = g
            rgb[3 * i + 1] = g
            rgb[3 * i + 2] = g
    elif colortype == 3:
        if plte is None:
            raise ValueError('%s: 调色板 PNG 缺少 PLTE' % path)
        for i in range(w * h):
            k = out[i] * 3
            rgb[3 * i:3 * i + 3] = plte[k:k + 3]
    elif colortype == 4:
        for i in range(w * h):
            g = out[2 * i]
            a = out[2 * i + 1]
            v = (g * a + 255 * (255 - a)) // 255
            rgb[3 * i] = v
            rgb[3 * i + 1] = v
            rgb[3 * i + 2] = v
    elif colortype == 6:
        for i in range(w * h):
            j = 4 * i
            a = out[j + 3]
            if a == 255:
                rgb[3 * i] = out[j]
                rgb[3 * i + 1] = out[j + 1]
                rgb[3 * i + 2] = out[j + 2]
            else:
                inv = 255 - a
                rgb[3 * i] = (out[j] * a + 255 * inv) // 255
                rgb[3 * i + 1] = (out[j + 1] * a + 255 * inv) // 255
                rgb[3 * i + 2] = (out[j + 2] * a + 255 * inv) // 255
    else:
        raise ValueError('%s: 不支持的色彩类型 %d' % (path, colortype))

    return w, h, bytes(rgb)


# ------------------------------------------------------------- 文档类
class PDFDocImg(PDFDoc):
    """在原 PDFDoc 上支持图片 XObject。"""

    def __init__(self):
        PDFDoc.__init__(self)
        self.images = {}        # name -> (objnum, w, h)
        self._img_by_path = {}  # 绝对路径(小写) -> (name, w, h)，避免重复嵌入
        self._seq = 0
        self._page_xo = {}      # 页面对象号 -> [图片名]
        self._outline = None    # set_outline() 产生的节点树

    # ---------------------------------------------------------- 大纲
    def set_outline(self, entries):
        """写入 PDF 侧边栏书签。

        entries: [(level, title, page_1based), ...]，level 1/2/3 自动嵌套。
        标题以 UTF-16BE 十六进制字符串写入，中文在阅读器中正常显示。
        """
        if not entries:
            return
        nodes = []
        for lvl, title, page in entries:
            nodes.append({'lvl': lvl, 'title': title, 'page': page,
                          'obj': self._alloc(), 'parent': None, 'children': []})
        roots = []
        stack = []
        for nd in nodes:
            while stack and stack[-1]['lvl'] >= nd['lvl']:
                stack.pop()
            if stack:
                nd['parent'] = stack[-1]
                stack[-1]['children'].append(nd)
            else:
                roots.append(nd)
            stack.append(nd)
        self._outlines_root = self._alloc()
        self._outline = (nodes, roots)

    def _count_desc(self, nd):
        n = len(nd['children'])
        for c in nd['children']:
            n += self._count_desc(c)
        return n

    def _build_outline_objs(self):
        """把大纲节点写入文档对象表（必须在 xref 之前调用，保证偏移正确）。"""
        nodes, roots = self._outline
        root_num = self._outlines_root
        by_parent = {}
        for nd in nodes:
            key = nd['parent']['obj'] if nd['parent'] else 0
            by_parent.setdefault(key, []).append(nd)
        for nd in nodes:
            sibs = by_parent[nd['parent']['obj'] if nd['parent'] else 0]
            i = sibs.index(nd)
            prev_n = sibs[i - 1]['obj'] if i > 0 else None
            next_n = sibs[i + 1]['obj'] if i + 1 < len(sibs) else None
            kids = nd['children']
            title_hex = (b'<FEFF'
                         + nd['title'].encode('utf-16-be').hex().upper().encode()
                         + b'>')
            pieces = [b'/Title ' + title_hex,
                      b'/Parent %d 0 R' % (nd['parent']['obj'] if nd['parent'] else root_num)]
            if prev_n:
                pieces.append(b'/Prev %d 0 R' % prev_n)
            if next_n:
                pieces.append(b'/Next %d 0 R' % next_n)
            if kids:
                pieces.append(b'/First %d 0 R' % kids[0]['obj'])
                pieces.append(b'/Last %d 0 R' % kids[-1]['obj'])
                pieces.append(b'/Count %d' % self._count_desc(nd))
            pg = nd['page'] - 1
            if 0 <= pg < len(self.pages_obj):
                pieces.append(b'/Dest [ %d 0 R /XYZ null null null ]' % self.pages_obj[pg])
            self.set(nd['obj'], ('raw', b'<< ' + b' '.join(pieces) + b' >>'))
        head = [b'/Type /Outlines']
        if roots:
            head.append(b'/First %d 0 R' % roots[0]['obj'])
            head.append(b'/Last %d 0 R' % roots[-1]['obj'])
        head.append(b'/Count %d' % len(nodes))
        self.set(root_num, ('raw', b'<< ' + b' '.join(head) + b' >>'))

    # ---------------------------------------------------------- 图片
    def add_image(self, path, name=None):
        # 同一路径只嵌入一次（排版时会预排一遍 + 正式排一遍，必须去重）
        key = os.path.abspath(path).lower()
        hit = self._img_by_path.get(key)
        if hit is not None:
            return hit
        w, h, rgb = decode_png(path)
        self._seq += 1
        if name is None:
            name = 'Im%d' % self._seq
        if name in self.images:
            raise ValueError('图片名重复: %s' % name)
        num = self._alloc()
        self.set(num, ('img', w, h, rgb))
        self.images[name] = (num, w, h)
        self._img_by_path[key] = (name, w, h)
        return name, w, h

    # ---------------------------------------------------------- 页面
    def add_page(self, items):
        ops = ['q']
        used = []
        for it in items:
            if it[0] == 'text':
                _, tag, size, x, y, color, text = it
                pf = self.fonts_by_tag[tag]
                gids = []
                for ch in text:
                    gid = pf.uni2gid.get(ord(ch))
                    if gid is None:
                        gid = pf.uni2gid.get(0x20, 0)
                    gids.append(gid)
                hexdata = b''.join(b'%04X' % g for g in gids).decode('ascii')
                ops.append(
                    'BT /%s %.2f Tf %.3f %.3f %.3f rg 1 0 0 1 %.2f %.2f Tm <%s> Tj ET'
                    % (tag, size, color[0], color[1], color[2], x, y, hexdata))
            elif it[0] == 'rule':
                _, x0, x1, y, color, width = it
                ops.append('%.3f %.3f %.3f rg %.3f %.3f %.3f %.3f re f'
                           % (color[0], color[1], color[2], x0, y, x1 - x0, width))
            elif it[0] == 'image':
                _, name, x, y, w, h = it
                if name not in used:
                    used.append(name)
                ops.append('q %.3f 0 0 %.3f %.3f %.3f cm /%s Do Q'
                           % (w, h, x, y, name))
        ops.append('Q')
        stream = zlib.compress('\n'.join(ops).encode('latin-1'))
        cnum = self._alloc()
        self.set(cnum, ('stream', stream))
        pnum = self._alloc()
        self.set(pnum, ('page', cnum))
        self._page_xo[pnum] = used
        self.pages_obj.append(pnum)

    # -------------------------------------------------------- 序列化
    def serialize(self):
        for pf in self.fonts:
            ff = self._alloc()
            desc = self._alloc()
            cid = self._alloc()
            pf._ff, pf._desc, pf._cid = ff, desc, cid
            self.set(ff, ('stream', pf.subset))
            self.set(desc, ('raw', (
                '<< /Type /FontDescriptor /FontName /%s /Flags %d '
                '/FontBBox [ -400 -400 1400 1000 ] /ItalicAngle 0 /Ascent 900 '
                '/Descent -220 /CapHeight 700 /StemV 80 /FontFile2 %d 0 R >>'
                % (pf.name, pf.flags, ff)).encode('latin-1')))
            w = b' '.join(b'%d [%d]' % (g, round(pf.advances[g] * 1000.0 / pf.upm))
                          for g in sorted(pf.advances.keys()))
            self.set(cid, ('raw', (
                '<< /Type /Font /Subtype /CIDFontType2 /BaseFont /%s '
                '/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> '
                '/FontDescriptor %d 0 R /CIDToGIDMap /Identity /DW 1000 /W [ '
                % (pf.name, desc)).encode('latin-1') + w + b' ] >>'))
            tu = ''
            if self.tounicode:
                cnum = self._alloc()
                self.set(cnum, ('stream', _tounicode_cmap(pf.uni2gid)))
                tu = ' /ToUnicode %d 0 R' % cnum
            self.set(pf._res, ('raw', (
                '<< /Type /Font /Subtype /Type0 /BaseFont /%s '
                '/Encoding /Identity-H /DescendantFonts [ %d 0 R ]%s >>'
                % (pf.name, cid, tu)).encode('latin-1')))

        pages_tree = self._alloc()
        catalog = self._alloc()
        kids = ' '.join('%d 0 R' % p for p in self.pages_obj)
        self.set(pages_tree, ('raw', (
            '<< /Type /Pages /Kids [ %s ] /Count %d >>'
            % (kids, len(self.pages_obj))).encode('latin-1')))
        if self._outline:
            cat = ('<< /Type /Catalog /Pages %d 0 R /Outlines %d 0 R '
                   '/PageMode /UseOutlines >>' % (pages_tree, self._outlines_root))
        else:
            cat = '<< /Type /Catalog /Pages %d 0 R >>' % pages_tree
        self.set(catalog, ('raw', cat.encode('latin-1')))
        if self._outline:
            self._build_outline_objs()

        n = len(self._obj)
        out = bytearray(b'%PDF-1.5\n%\xe2\xe3\xcf\xd3\n')
        offsets = {}
        font_res = b' '.join(b'/%s %d 0 R' % (f.tag.encode('latin-1'), f._res)
                             for f in self.fonts)
        for i in range(1, n + 1):
            obj = self._obj[i - 1]
            offsets[i] = len(out)
            if obj is None:
                out += b'%d 0 obj null endobj\n' % i
            elif obj[0] == 'stream':
                data = obj[1]
                out += (b'%d 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n'
                        % (i, len(data)))
                out += data + b'\nendstream\nendobj\n'
            elif obj[0] == 'img':
                _, iw, ih, rgb = obj
                data = zlib.compress(rgb, 6)
                out += (b'%d 0 obj\n<< /Type /XObject /Subtype /Image /Width %d '
                        b'/Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 '
                        b'/Filter /FlateDecode /Length %d >>\nstream\n'
                        % (i, iw, ih, len(data)))
                out += data + b'\nendstream\nendobj\n'
            elif obj[0] == 'raw':
                out += b'%d 0 obj\n' % i + obj[1] + b'\nendobj\n'
            elif obj[0] == 'page':
                cnum = obj[1]
                xo = self._page_xo.get(i, [])
                xostr = b''
                if xo:
                    xostr = b' /XObject << ' + b' '.join(
                        b'/%s %d 0 R' % (nm.encode('latin-1'), self.images[nm][0])
                        for nm in xo) + b' >>'
                out += (b'%d 0 obj\n<< /Type /Page /Parent %d 0 R '
                        b'/MediaBox [ 0 0 595.276 841.89 ] '
                        b'/Resources << /Font <<%s>>%s >> /Contents %d 0 R >>\nendobj\n'
                        % (i, pages_tree, font_res, xostr, cnum))
            else:
                out += b'%d 0 obj null endobj\n' % i

        xref = len(out)
        out += b'xref\n0 %d\n' % (n + 1)
        out += b'0000000000 65535 f \n'
        for i in range(1, n + 1):
            out += b'%010d 00000 n \n' % offsets[i]
        out += (b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n'
                % (n + 1, catalog, xref))
        return bytes(out)

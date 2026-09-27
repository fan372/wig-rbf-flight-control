# -*- coding: utf-8 -*-
"""Pure-stdlib PDF generator with embedded TrueType subset fonts."""
import struct, zlib

# ---------------------------------------------------------------
# TTF / TTC parsing
# ---------------------------------------------------------------
class TTFont:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        self.tables = {}
        self._parse()

    def _parse(self):
        d = self.data
        tag = d[0:4]
        if tag == b'ttcf':
            off = struct.unpack('>I', d[12:16])[0]
            self._parse_sfnt(d, off)
        elif tag in (b'\x00\x01\x00\x00', b'true'):
            self._parse_sfnt(d, 0)
        else:
            raise ValueError('unsupported font file')

    def _parse_sfnt(self, d, base):
        num = struct.unpack('>H', d[base+4:base+6])[0]
        for i in range(num):
            o = base + 12 + i*16
            t = d[o:o+4].decode('latin-1')
            checksum, offset, length = struct.unpack('>III', d[o+4:o+16])
            self.tables[t] = d[offset:offset+length]

    def u16(self, tag, off):
        return struct.unpack('>H', self.tables[tag][off:off+2])[0]

    def i16(self, tag, off):
        return struct.unpack('>h', self.tables[tag][off:off+2])[0]

    @property
    def units_per_em(self):
        return self.u16('head', 18)

    @property
    def num_glyphs(self):
        return self.u16('maxp', 4)

    def num_hmetrics(self):
        return self.u16('hhea', 34)

    def cmap_mapping(self):
        cmap = self.tables['cmap']
        n = struct.unpack('>H', cmap[2:4])[0]
        best = None
        for i in range(n):
            plat, enc, off = struct.unpack('>HHI', cmap[4+i*8:12+i*8])
            fmt = struct.unpack('>H', cmap[off:off+2])[0]
            sc = 0
            if plat == 3 and enc == 1: sc = 3
            elif plat == 0: sc = 2
            elif plat == 3 and enc == 10: sc = 1
            if fmt not in (4, 12): sc = 0
            if best is None or sc > best[0]:
                best = (sc, fmt, off)
        if best is None or best[0] == 0:
            raise ValueError('no usable cmap in font')
        _, fmt, off = best
        if fmt == 4:
            return self._cmap4(cmap, off)
        return self._cmap12(cmap, off)

    def _cmap4(self, cmap, off):
        segX2 = struct.unpack('>H', cmap[off+6:off+8])[0]
        seg_count = segX2 // 2
        base = off + 14
        end = struct.unpack('>%dH' % seg_count, cmap[base:base+segX2])
        start = struct.unpack('>%dH' % seg_count, cmap[base+segX2+2:base+2*segX2+2])
        delta = struct.unpack('>%dH' % seg_count, cmap[base+2*segX2+2:base+3*segX2+2])
        ro_off = base + 3*segX2 + 2
        range_o = struct.unpack('>%dH' % seg_count, cmap[ro_off:ro_off+segX2])
        out = {}
        for s in range(seg_count):
            for c in range(start[s], end[s]+1):
                if c == 0xFFFF: continue
                if range_o[s] == 0:
                    g = (c + delta[s]) & 0xFFFF
                else:
                    gi = ro_off + s*2 + range_o[s] + (c-start[s])*2
                    g = struct.unpack('>H', cmap[gi:gi+2])[0]
                    if g: g = (g + delta[s]) & 0xFFFF
                if g: out[c] = g
        return out

    def _cmap12(self, cmap, off):
        n = struct.unpack('>I', cmap[off+12:off+16])[0]
        out = {}
        pos = off + 16
        for _ in range(n):
            st, en, sg = struct.unpack('>III', cmap[pos:pos+12]); pos += 12
            for c in range(st, en+1):
                out[c] = sg + (c - st)
        return out

    def advance(self, gid):
        hhea = self.tables['hhea']
        nh = struct.unpack('>H', hhea[34:36])[0]
        hmtx = self.tables['hmtx']
        if gid < nh:
            return struct.unpack('>H', hmtx[gid*4:gid*4+2])[0]
        return struct.unpack('>H', hmtx[(nh-1)*4:(nh-1)*4+2])[0]

    def glyph_data(self, gid):
        loca = self.tables['loca']
        short = self.i16('head', 50) == 0
        n = self.num_glyphs
        if short:
            loc = [struct.unpack('>H', loca[i*2:i*2+2])[0]*2 for i in range(n+1)]
        else:
            loc = [struct.unpack('>I', loca[i*4:i*4+4])[0] for i in range(n+1)]
        return self.tables.get('glyf', b'')[loc[gid]:loc[gid+1]]

# ---------------------------------------------------------------
# subsetting: keeps ORIGINAL glyph ids
# ---------------------------------------------------------------
def _checksum(data):
    pad = b'\x00' * ((4 - len(data) % 4) % 4)
    d = data + pad
    return sum(struct.unpack('>I', d[i:i+4])[0] for i in range(0, len(d), 4)) & 0xFFFFFFFF

def _glyphs_needed(font, cmap, wanted):
    """Return set of original glyph ids needed for wanted unicode chars."""
    needed = set()
    stack = [cmap[c] for c in wanted if c in cmap]
    while stack:
        gid = stack.pop()
        if gid in needed:
            continue
        needed.add(gid)
        data = font.glyph_data(gid)
        if len(data) >= 10 and struct.unpack('>h', data[0:2])[0] < 0:
            pos = 10
            while pos + 4 <= len(data):
                flags, child = struct.unpack('>HH', data[pos:pos+4])
                pos += 4
                if flags & 0x0001: pos += 4
                elif flags & 0x0002: pos += 2
                if flags & 0x0008: pos += 2
                elif flags & 0x0040: pos += 4
                elif flags & 0x0080: pos += 8
                if child not in needed:
                    stack.append(child)
                if not (flags & 0x0020): break
    return needed


def subset_ttf(font, used_chars):
    """Subset a TrueType font, PRESERVING original GID numbering.

    Returns (font_bytes, {unicode_ord: original_gid},
             {original_gid: advance_units}, units_per_em).
    """
    cmap = font.cmap_mapping()
    used_int = set(ord(c) for c in used_chars)
    wanted = sorted(used_int & set(cmap.keys()))
    needed = _glyphs_needed(font, cmap, wanted)
    num_glyphs = font.num_glyphs

    # ---- glyf / loca: only glyphs in `needed` keep data, others empty ----
    glyf_offset = [0] * (num_glyphs + 1)
    glyf_parts = []
    cursor = 0
    for gid in range(num_glyphs + 1):
        glyf_offset[gid] = cursor
        if gid in needed:
            data = bytearray(font.glyph_data(gid))
            if len(data) >= 10 and struct.unpack('>h', data[0:2])[0] < 0:
                pos = 10
                while pos + 4 <= len(data):
                    flags = struct.unpack('>H', data[pos:pos+2])[0]
                    child = struct.unpack('>H', data[pos+2:pos+4])[0]
                    if child not in needed:
                        child = 0
                    data[pos+2:pos+4] = struct.pack('>H', child)
                    pos += 4
                    if flags & 0x0001: pos += 4
                    elif flags & 0x0002: pos += 2
                    if flags & 0x0008: pos += 2
                    elif flags & 0x0040: pos += 4
                    elif flags & 0x0080: pos += 8
                    if not (flags & 0x0020): break
            while len(data) % 4:
                data.append(0)
            glyf_parts.append(bytes(data))
            cursor += len(data)
    glyf = b''.join(glyf_parts)
    loca = b''.join(struct.pack('>I', v) for v in glyf_offset)

    # ---- hmtx: full-length, original order ----
    nh = font.num_hmetrics()
    hmtx_parts = []
    advances = {}
    for gid in range(num_glyphs):
        if gid in needed:
            adv = max(font.advance(gid), 0)
            advances[gid] = adv
        else:
            adv = 0
        hmtx_parts.append(struct.pack('>Hh', adv, 0))
    hmtx = b''.join(hmtx_parts)
    hhea = bytearray(font.tables['hhea'])
    hhea[34:36] = struct.pack('>H', num_glyphs)  # all metrics explicit

    # ---- cmap format 4 (used chars only) ----
    uni2gid = {c: cmap[c] for c in wanted}
    chars = sorted(uni2gid.keys())
    segs = [(c, c, (uni2gid[c] - c) & 0xFFFF) for c in chars]
    segs.append((0xFFFF, 0xFFFF, 0x0001))
    seg_count = len(segs)
    segX2 = seg_count * 2
    end = b''.join(struct.pack('>H', s[1]) for s in segs)
    start = b''.join(struct.pack('>H', s[0]) for s in segs)
    delta = b''.join(struct.pack('>H', s[2]) for s in segs)
    ranges = b'\x00\x00' * seg_count
    seg_count_ceil = 1
    while seg_count_ceil * 2 < seg_count:
        seg_count_ceil *= 2
    search_range = seg_count_ceil * 2
    entry_selector = 0
    while (1 << (entry_selector + 1)) <= seg_count_ceil:
        entry_selector += 1
    range_shift = segX2 - search_range
    cmap4 = struct.pack('>HHHHHHH', 4, 16 + segX2 * 4, 0, segX2,
                        search_range, entry_selector, range_shift)
    cmap4 += end + b'\x00\x00' + start + delta + ranges
    cmap = b'\x00\x00' + struct.pack('>H', 1) + \
        struct.pack('>HHI', 3, 1, 12) + cmap4

    # ---- head ----
    head = bytearray(font.tables['head'])
    head[0:4] = struct.pack('>I', 0x00010000)
    head[50:52] = struct.pack('>h', 1)
    head[8:12] = b'\x00\x00\x00\x00'
    head = bytes(head)

    # ---- name (minimal, valid) ----
    labels = ((1, 'Subset'), (2, 'Regular'), (4, 'Subset Regular'), (6, 'SubsetFont'))
    name_recs = b''; payload = b''
    for nid, label in labels:
        b = label.encode('latin-1')
        name_recs += struct.pack('>HHHH', 3, 1, 0x0409, nid) + struct.pack('>HH', len(b), len(payload))
        payload += b
    name = struct.pack('>HHH', 0, len(labels), 6 + len(labels) * 12)
    name += name_recs + payload

    post = struct.pack('>I', 0x00030000) + b'\x00'*28
    maxp = bytearray(font.tables['maxp'])
    maxp[4:6] = struct.pack('>H', num_glyphs)
    maxp = bytes(maxp)

    tables = {'cmap': cmap, 'head': head, 'hhea': bytes(hhea), 'hmtx': hmtx,
              'maxp': maxp, 'name': name, 'post': post, 'glyf': glyf,
              'loca': loca}
    for t in ('cvt ', 'fpgm', 'prep', 'OS/2', 'gasp'):
        if t in font.tables:
            tables[t] = font.tables[t]
    names = sorted(tables.keys())
    num = len(names)
    header = struct.pack('>IHHHH', 0x00010000, num, 0, 0, 0)
    offset = len(header) + 16*num
    dirs = b''; body = b''
    head_off_in_output = None
    for t in names:
        d = tables[t]
        while offset % 4:
            body += b'\x00'; offset += 1
        if t == 'head':
            head_off_in_output = offset
        dirs += struct.pack('>4sIII', t.encode('latin-1'), _checksum(d), offset, len(d))
        body += d
        offset += len(d)
    out = bytearray(header + dirs + body)
    adj_pos = head_off_in_output + 8
    out[adj_pos:adj_pos+4] = b'\x00\x00\x00\x00'
    total = sum(struct.unpack('>I', out[i:i+4])[0] for i in range(0, len(out) - len(out) % 4, 4)) & 0xFFFFFFFF
    out[adj_pos:adj_pos+4] = struct.pack('>I', (0xB1B0AFBA - total) & 0xFFFFFFFF)
    head_cs = _checksum(bytes(out[head_off_in_output:head_off_in_output+len(tables['head'])]))
    dir_off = 12 + 16 * names.index('head')
    out[dir_off+4:dir_off+8] = struct.pack('>I', head_cs)
    return bytes(out), uni2gid, advances, font.units_per_em

# ---------------------------------------------------------------
# ToUnicode CMap (opt-in): keeps copy/paste + search working
# ---------------------------------------------------------------
def _utf16be_hex(cp):
    if cp > 0xFFFF:
        v = cp - 0x10000
        return '%04X%04X' % (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF))
    return '%04X' % cp


def _tounicode_cmap(uni2gid):
    """Build a compressed ToUnicode CMap stream mapping GID -> Unicode."""
    gid2uni = {}
    for uni, gid in uni2gid.items():
        gid2uni.setdefault(gid, uni)
    lines = [
        '/CIDInit /ProcSet findresource begin',
        '12 dict begin',
        'begincmap',
        '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def',
        '/CMapName /Adobe-Identity-UCS def',
        '/CMapType 2 def',
        '1 begincodespacerange',
        '<0000> <FFFF>',
        'endcodespacerange',
    ]
    items = sorted(gid2uni.items())
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        lines.append('%d beginbfchar' % len(chunk))
        for gid, uni in chunk:
            lines.append('<%04X> <%s>' % (gid, _utf16be_hex(uni)))
        lines.append('endbfchar')
    lines += ['endcmap', 'CMapName currentdict /CMap defineresource pop',
              'end', 'end']
    return zlib.compress('\n'.join(lines).encode('latin-1'))


# ---------------------------------------------------------------
# PDF writer
# ---------------------------------------------------------------
class PdfFont:
    def __init__(self, tag, name, subset_bytes, uni2gid, advances, upm, flags=4):
        self.tag = tag
        self.name = name
        self.subset = subset_bytes
        self.uni2gid = uni2gid
        self.advances = advances
        self.upm = upm
        self.flags = flags
        self._res = None

    def width_pt(self, gid, size_pt):
        adv = self.advances.get(gid, 0)
        return adv * size_pt / self.upm


class PDFDoc:
    def __init__(self):
        self._obj = []
        self.fonts = []
        self.pages_obj = []
        self.tounicode = False

    def enable_tounicode(self):
        """Opt in to /ToUnicode CMaps so the PDF text stays copyable/searchable.

        Off by default, so existing outputs are unchanged. Chinese text is
        written as Identity-H CIDs; without this map a reader cannot recover
        the Unicode characters behind the glyph ids.
        """
        self.tounicode = True
        return self

    def _alloc(self):
        self._obj.append(None)
        return len(self._obj)

    def set(self, num, obj):
        self._obj[num-1] = obj

    def add_font(self, pdf_font):
        pdf_font._res = self._alloc()
        self.fonts.append(pdf_font)
        return pdf_font.tag

    @property
    def fonts_by_tag(self):
        return {f.tag: f for f in self.fonts}

    def add_page(self, items):
        ops = ['q']
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
                ops.append('BT /%s %.2f Tf %.3f %.3f %.3f rg 1 0 0 1 %.2f %.2f Tm <%s> Tj ET'
                           % (tag, size, color[0], color[1], color[2], x, y, hexdata))
            elif it[0] == 'rule':
                _, x0, x1, y, color, width = it
                ops.append('%.3f %.3f %.3f %.3f re f' % (x0, y, x1 - x0, width))
        ops.append('Q')
        stream = zlib.compress('\n'.join(ops).encode('latin-1'))
        cnum = self._alloc()
        self.set(cnum, ('stream', stream))
        pnum = self._alloc()
        self.set(pnum, ('page', cnum))
        self.pages_obj.append(pnum)

    def serialize(self):
        for pf in self.fonts:
            ff = self._alloc(); desc = self._alloc(); cid = self._alloc()
            pf._ff, pf._desc, pf._cid = ff, desc, cid
            self.set(ff, ('stream', pf.subset))
            self.set(desc, ('raw', ('<< /Type /FontDescriptor /FontName /%s /Flags %d '
                                    '/FontBBox [ -400 -400 1400 1000 ] /ItalicAngle 0 /Ascent 900 '
                                    '/Descent -220 /CapHeight 700 /StemV 80 /FontFile2 %d 0 R >>'
                                    % (pf.name, pf.flags, ff)).encode('latin-1')))
            w = b' '.join(b'%d [%d]' % (g, round(pf.advances[g] * 1000.0 / pf.upm))
                          for g in sorted(pf.advances.keys()))
            self.set(cid, ('raw', ('<< /Type /Font /Subtype /CIDFontType2 /BaseFont /%s '
                                   '/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> '
                                   '/FontDescriptor %d 0 R /CIDToGIDMap /Identity /DW 1000 /W [ '
                                   % (pf.name, desc)).encode('latin-1') + w + b' ] >>'))
            tu = ''
            if self.tounicode:
                cnum = self._alloc()
                self.set(cnum, ('stream', _tounicode_cmap(pf.uni2gid)))
                tu = ' /ToUnicode %d 0 R' % cnum
            self.set(pf._res, ('raw', ('<< /Type /Font /Subtype /Type0 /BaseFont /%s '
                                       '/Encoding /Identity-H /DescendantFonts [ %d 0 R ]%s >>'
                                       % (pf.name, cid, tu)).encode('latin-1')))
        pages_tree = self._alloc()
        catalog = self._alloc()
        kids = ' '.join('%d 0 R' % p for p in self.pages_obj)
        self.set(pages_tree, ('raw', ('<< /Type /Pages /Kids [ %s ] /Count %d >>'
                                      % (kids, len(self.pages_obj))).encode('latin-1')))
        self.set(catalog, ('raw', ('<< /Type /Catalog /Pages %d 0 R >>' % pages_tree).encode('latin-1')))
        n = len(self._obj)
        offsets = {}
        out = bytearray(b'%PDF-1.5\n%\xe2\xe3\xcf\xd3\n')
        font_res = b' '.join(b'/%s %d 0 R' % (f.tag.encode('latin-1'), f._res) for f in self.fonts)
        for i in range(1, n+1):
            obj = self._obj[i-1]
            offsets[i] = len(out)
            if obj is None:
                out += b'%d 0 obj null endobj\n' % i
            elif isinstance(obj, tuple) and obj[0] == 'stream':
                data = obj[1]
                out += b'%d 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n' % (i, len(data))
                out += data + b'\nendstream\nendobj\n'
            elif isinstance(obj, tuple) and obj[0] == 'raw':
                out += b'%d 0 obj\n' % i + obj[1] + b'\nendobj\n'
            elif isinstance(obj, tuple) and obj[0] == 'page':
                cnum = obj[1]
                out += (b'%d 0 obj\n<< /Type /Page /Parent %d 0 R /MediaBox [ 0 0 595.276 841.89 ] '
                        b'/Resources << /Font <<%s>> >> /Contents %d 0 R >>\nendobj\n'
                        % (i, pages_tree, font_res, cnum))
            else:
                out += b'%d 0 obj\n' % i + bytes(obj) + b'\nendobj\n'
        xref = len(out)
        out += b'xref\n0 %d\n' % (n+1)
        out += b'0000000000 65535 f \n'
        for i in range(1, n+1):
            out += b'%010d 00000 n \n' % offsets[i]
        out += b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (n+1, catalog, xref)
        return bytes(out)

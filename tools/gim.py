"""GIM (MIG.00.1PSP) decode / re-encode (same format, same size)."""
import struct
from PIL import Image

def blocks(b):
    """-> dict with 'img' and 'pal' info (first picture only)"""
    out = {}
    pos = 0x10
    while pos + 16 <= len(b):
        t, _, size, nxt, doff = struct.unpack_from('<HHIII', b, pos)
        if t in (2, 3):
            pos += doff; continue
        if t in (4, 5):
            d = pos + doff
            hl, _, fmt, order, w, h, bpp, pa, ha = struct.unpack_from('<HHHHHHHHH', b, d)
            poff = struct.unpack_from('<I', b, d + 0x1c)[0]
            key = 'img' if t == 4 else 'pal'
            if key not in out:
                out[key] = dict(fmt=fmt, order=order, w=w, h=h, bpp=bpp, pa=pa, ha=ha, data=d + poff,
                                end=pos + size)
        if size == 0: break
        pos += size
    return out

BPP = {0: 16, 1: 16, 2: 16, 3: 32, 4: 4, 5: 8}

def geom(im):
    bpp = BPP[im['fmt']]
    pitch = (im['w'] * bpp + 7) // 8
    pitch = (pitch + 15) // 16 * 16
    hh = (im['h'] + 7) // 8 * 8 if im['order'] else im['h']
    return bpp, pitch, hh

def unswizzle(raw, pitch, hh):
    out = bytearray(len(raw))
    bw = pitch // 16
    i = 0
    for by in range(hh // 8):
        for bx in range(bw):
            for y in range(8):
                o = (by * 8 + y) * pitch + bx * 16
                out[o:o + 16] = raw[i:i + 16]; i += 16
    return out

def swizzle(lin, pitch, hh):
    out = bytearray(len(lin))
    bw = pitch // 16
    i = 0
    for by in range(hh // 8):
        for bx in range(bw):
            for y in range(8):
                o = (by * 8 + y) * pitch + bx * 16
                out[i:i + 16] = lin[o:o + 16]; i += 16
    return out

def px16(v, fmt):
    if fmt == 0:
        return ((v & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, ((v >> 11) & 31) * 255 // 31, 255)
    if fmt == 1:
        return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31, 255 if v >> 15 else 0)
    return ((v & 15) * 17, ((v >> 4) & 15) * 17, ((v >> 8) & 15) * 17, (v >> 12) * 17)

def to16(c, fmt):
    r, g, b_, a = c
    if fmt == 0: return (r * 31 // 255) | ((g * 63 // 255) << 5) | ((b_ * 31 // 255) << 11)
    if fmt == 1: return (r * 31 // 255) | ((g * 31 // 255) << 5) | ((b_ * 31 // 255) << 10) | ((a >= 128) << 15)
    return (r // 17) | ((g // 17) << 4) | ((b_ // 17) << 8) | ((a // 17) << 12)

def read_pal(b, p):
    n = p['w']
    if p['fmt'] == 3:
        return [tuple(b[p['data'] + 4 * i:p['data'] + 4 * i + 4]) for i in range(n)]
    return [px16(struct.unpack_from('<H', b, p['data'] + 2 * i)[0], p['fmt']) for i in range(n)]

def linear(b, im):
    bpp, pitch, hh = geom(im)
    raw = b[im['data']:im['data'] + pitch * hh]
    if len(raw) < pitch * hh: raw = raw + bytes(pitch * hh - len(raw))
    return (unswizzle(raw, pitch, hh) if im['order'] else bytearray(raw)), bpp, pitch

def decode(b):
    bl = blocks(b); im = bl['img']
    lin, bpp, pitch = linear(b, im)
    w, h, fmt = im['w'], im['h'], im['fmt']
    pal = read_pal(b, bl['pal']) if 'pal' in bl else None
    out = Image.new('RGBA', (w, h)); px = out.load()
    for y in range(h):
        row = y * pitch
        for x in range(w):
            if fmt == 4:
                v = lin[row + x // 2]; v = (v >> 4) if x & 1 else (v & 15); c = pal[v]
            elif fmt == 5: c = pal[lin[row + x]]
            elif fmt == 3: c = tuple(lin[row + 4 * x:row + 4 * x + 4])
            else: c = px16(struct.unpack_from('<H', lin, row + 2 * x)[0], fmt)
            px[x, y] = c
    return out

def encode(b, img, keep_pal=True):
    """write RGBA img (same size) into GIM b, keeping format. Indexed: new palette (same size)."""
    b = bytearray(b); bl = blocks(b); im = bl['img']
    bpp, pitch, hh = geom(im)
    w, h, fmt = im['w'], im['h'], im['fmt']
    img = img.convert('RGBA'); assert img.size == (w, h), (img.size, w, h)
    lin = bytearray(pitch * hh)
    if fmt in (4, 5):
        p = bl['pal']; n = p['w']
        if keep_pal:
            pal = read_pal(bytes(b), p)
            idx = nearest(img, pal)
        else:
            q = quantize(img, n)
            pal = q[1]; idx = q[0]
        for y in range(h):
            for x in range(w):
                v = idx[y * w + x]
                if fmt == 4:
                    o = y * pitch + x // 2
                    lin[o] |= (v << 4) if x & 1 else v
                else: lin[y * pitch + x] = v
        for i in range(n if not keep_pal else 0):
            c = pal[i] if i < len(pal) else (0, 0, 0, 0)
            if p['fmt'] == 3: b[p['data'] + 4 * i:p['data'] + 4 * i + 4] = bytes(c)
            else: struct.pack_into('<H', b, p['data'] + 2 * i, to16(c, p['fmt']))
    else:
        px = img.load()
        for y in range(h):
            for x in range(w):
                c = px[x, y]
                if fmt == 3: lin[y * pitch + 4 * x:y * pitch + 4 * x + 4] = bytes(c)
                else: struct.pack_into('<H', lin, y * pitch + 2 * x, to16(c, fmt))
    raw = swizzle(lin, pitch, hh) if im['order'] else lin
    n = min(len(raw), len(b) - im['data'])
    b[im['data']:im['data'] + n] = raw[:n]
    return bytes(b)

def quantize(img, n):
    """RGBA-aware quantize -> (index list, palette list of RGBA)"""
    px = list(img.getdata())
    # k-means-lite via PIL on premultiplied RGBA packed into RGB+A trick: quantize RGBA directly
    q = img.quantize(colors=n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = q.getpalette('RGBA') if hasattr(q, 'getpalette') else None
    try:
        pal = q.getpalette(rawmode='RGBA')
    except TypeError:
        pass
    idx = list(q.getdata())
    cols = [tuple(pal[4 * i:4 * i + 4]) for i in range(len(pal) // 4)] if pal and len(pal) % 4 == 0 else None
    if cols is None or len(cols) < max(idx) + 1:
        # fallback: compute mean RGBA per index
        acc = {}
        for i, c in zip(idx, px):
            a = acc.setdefault(i, [0, 0, 0, 0, 0])
            for k in range(4): a[k] += c[k]
            a[4] += 1
        cols = [(0, 0, 0, 0)] * n
        for i, a in acc.items(): cols[i] = tuple(a[k] // a[4] for k in range(4))
    return idx, cols[:n]

def nearest(img, pal):
    import numpy as np
    a = np.asarray(img, dtype=np.int32).reshape(-1, 4)
    P = np.asarray(pal, dtype=np.int32)
    # premultiplied-ish distance: colour weighted by alpha, plus alpha
    af = a[:, 3:4] / 255.0; pf = P[:, 3:4] / 255.0
    ac = np.concatenate([a[:, :3] * af, a[:, 3:4]], 1)
    pc = np.concatenate([P[:, :3] * pf, P[:, 3:4]], 1)
    uniq, inv = np.unique(ac.round().astype(np.int32), axis=0, return_inverse=True)
    best = np.empty(len(uniq), dtype=np.int64)
    for i in range(0, len(uniq), 4096):
        d = ((uniq[i:i+4096, None, :] - pc[None, :, :]) ** 2).sum(-1)
        best[i:i+4096] = d.argmin(1)
    return best[inv.reshape(-1)].tolist()

"""CSVB tables: Info(u16 rowsize,u16 nrows,...), OfsB(column offsets, ffff end), KITB, TblB(rows + string pool), Term.
String columns hold u32 offsets (relative to TblB data start) into a NUL-terminated pool."""
import struct

def chunks(b):
    p = 8; out = {}
    while p + 8 <= len(b):
        t = b[p:p + 4]; s = struct.unpack_from('<I', b, p + 4)[0]
        out[t] = (p, s)
        if s == 0: break
        p += s
    return out

class CSVB:
    def __init__(s, b):
        s.b = bytes(b)
        s.ch = chunks(b)
        s.rs, s.nr = struct.unpack_from('<HH', b, 16)
        p, sz = s.ch[b'OfsB']
        cols = []
        for k in range((sz - 8) // 2):
            v = struct.unpack_from('<H', b, p + 8 + 2 * k)[0]
            if v == 0xFFFF: break
            cols.append(v)
        s.cols = cols
        p, sz = s.ch[b'TblB']
        s.tp, s.tsz = p, sz
        s.d0 = p + 8
        s.pool0 = s.rs * s.nr
        s.pool = b[s.d0 + s.pool0:p + sz]
        starts = {0}
        for i, c in enumerate(s.pool):
            if c == 0 and i + 1 < len(s.pool): starts.add(i + 1)
        s.starts = starts
        # detect string columns (4-byte fields whose values all point at string starts)
        s.strcols = []
        for ci, c in enumerate(s.cols):
            end = s.cols[ci + 1] if ci + 1 < len(s.cols) else s.rs
            if end - c < 4 or c % 4: continue
            vals = [struct.unpack_from('<I', b, s.d0 + r * s.rs + c)[0] for r in range(s.nr)]
            good = [v for v in vals if v not in (0xFFFFFFFF, 0)]
            if good and all(s.pool0 <= v < s.pool0 + len(s.pool) for v in good):
                try:
                    for v in good: s.get(v).decode('cp932')
                except (UnicodeDecodeError, ValueError):
                    continue
                s.strcols.append(c)

    def get(s, v):
        o = v - s.pool0
        return s.pool[o:s.pool.index(b'\0', o)]

    def strings(s):
        """yield (row, col, bytes)"""
        for r in range(s.nr):
            for c in s.strcols:
                v = struct.unpack_from('<I', s.b, s.d0 + r * s.rs + c)[0]
                if v in (0xFFFFFFFF, 0): continue
                yield r, c, s.get(v)

    def rebuild(s, tr):
        """tr: function(bytes)->bytes|None. Original pool is kept intact (it may hold binary
        blobs); changed strings are appended to the pool and their pointers redirected."""
        b = bytearray(s.b)
        rows = bytearray(b[s.d0:s.d0 + s.pool0])
        pool = bytearray(s.pool); seen = {}
        while len(pool) % 4: pool += b'\0'
        for r in range(s.nr):
            for c in s.strcols:
                v = struct.unpack_from('<I', rows, r * s.rs + c)[0]
                if v in (0xFFFFFFFF, 0): continue
                ns = tr(s.get(v))
                if ns is None or ns == s.get(v): continue
                if ns not in seen:
                    seen[ns] = s.pool0 + len(pool); pool += ns + b'\0'
                struct.pack_into('<I', rows, r * s.rs + c, seen[ns])
        while len(pool) % 4: pool += b'\0'
        tbl = b'TblB' + struct.pack('<I', 8 + len(rows) + len(pool)) + rows + pool
        out = b[:s.tp] + tbl + b[s.tp + s.tsz:]
        out = bytearray(out)
        struct.pack_into('<I', out, 4, len(out))
        return bytes(out)

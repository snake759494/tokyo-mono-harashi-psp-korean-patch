"""ZNTP texture container: u32 'ZNTP', size, n, then n gim offsets, n name offsets."""
import struct
def entries(d):
    if d[:4] != b'ZNTP': return []
    n = struct.unpack_from('<I', d, 8)[0]
    offs = [o + 12 for o in struct.unpack_from('<%dI' % n, d, 12)]
    noffs = [o + 12 + 4 * n for o in struct.unpack_from('<%dI' % n, d, 12 + 4 * n)]
    out = []
    for i in range(n):
        end = offs[i + 1] if i + 1 < n else noffs[0]
        nm = d[noffs[i]:d.index(b'\0', noffs[i])].decode('ascii', 'replace')
        out.append((nm, offs[i], end))
    return out
def get(d, name):
    for nm, s, e in entries(d):
        if nm == name: return d[s:e]
    raise KeyError(name)
def put(d, name, g):
    d = bytearray(d)
    for nm, s, e in entries(d):
        if nm == name:
            assert len(g) <= e - s; d[s:s + len(g)] = g; return bytes(d)
    raise KeyError(name)

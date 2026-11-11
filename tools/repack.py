"""Patch files inside CROW.PAK (recursively through inner .pak / .zdv) and write a new ISO.
patches: {expanded_path: bytes}, paths as produced by tree.expand (".zdv" stripped)."""
import sys, os, io, struct, zlib, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak
from zdv import unzdv

def zdv(b):
    c = zlib.compress(b, 6)
    return struct.pack('<4I', len(b), len(b), 1, len(c)) + c

def rebuild_inner(b, children):
    """b: inner pak bytes; children: {relpath: newbytes} (relpath inside this pak, zdv stripped)"""
    t = pak.read_toc(io.BytesIO(b))
    ds = t['dstart']
    datas = []
    for p, (n, o, s) in zip(t['paths'], t['files']):
        datas.append(b[ds + o:ds + o + s])
    for i, p in enumerate(t['paths']):
        key = p[:-4] if p.endswith('.zdv') else p
        sub = {k[len(key):].lstrip('/'): v for k, v in children.items()
               if k == key or k.startswith(key + '/')}
        if sub:
            datas[i] = apply(datas[i], p, sub)
    order = sorted(range(len(datas)), key=lambda i: t['files'][i][1])
    hdr = bytearray(b[:ds])
    body = bytearray()
    fo = 16 + t['nd'] * 12
    for i in order:
        while len(body) % 4: body += b'\0'
        struct.pack_into('<III', hdr, fo + i * 12, t['files'][i][0], len(body), len(datas[i]))
        body += datas[i]
    return bytes(hdr + body)

def apply(b, name, sub):
    """sub: {relpath: bytes}; '' = replace this (decompressed) file"""
    if name.endswith('.zdv'):
        inner = unzdv(b)
        new = apply(inner, name[:-4], sub)
        return zdv(new)
    if '' in sub:
        return sub['']
    return rebuild_inner(b, sub)

def iso_find(iso_path, target):
    import pycdlib
    iso = pycdlib.PyCdlib(); iso.open(iso_path)
    rec = iso.get_record(iso_path=target)
    lba, size = rec.extent_location(), rec.data_length
    iso.close()
    return lba, size

def build(src_iso, out_iso, patches, eboot=None):
    lba, size = iso_find(src_iso, '/PSP_GAME/USRDIR/CROW.PAK')
    if os.path.exists(out_iso): os.remove(out_iso)
    shutil.copyfile(src_iso, out_iso)
    f = open(out_iso, 'r+b')
    base = lba * 2048
    f.seek(base); hb = f.read(16)
    nd, nf, ne, ds = struct.unpack('<4I', hb)
    f.seek(base); toc_b = f.read(ds)
    t = pak.read_toc(io.BytesIO(toc_b + b'\0' * 16))
    toc = bytearray(toc_b)
    offs = sorted(set(o for n, o, s in t['files']))
    slot_end = {}
    for i, o in enumerate(offs):
        slot_end[o] = offs[i + 1] if i + 1 < len(offs) else size - ds
    end = size - ds
    groups = {}
    for k, v in patches.items():
        for i, p in enumerate(t['paths']):
            key = p[:-4] if p.endswith('.zdv') else p
            if k == key or k.startswith(key + '/'):
                groups.setdefault(i, {})[k[len(key):].lstrip('/')] = v
                break
        else:
            raise KeyError(k)
    fo = 16 + nd * 12
    for i, sub in groups.items():
        n, o, s = t['files'][i]
        f.seek(base + ds + o); old = f.read(s)
        new = apply(old, t['paths'][i], sub)
        if o + len(new) <= slot_end[o]:
            no = o
        else:
            no = (end + 0x7FF) & ~0x7FF
            end = no + len(new)
        f.seek(base + ds + no); f.write(new)
        struct.pack_into('<III', toc, fo + i * 12, n, no, len(new))
    f.seek(base); f.write(toc)
    newsize = max(size, ds + end)
    if newsize != size:
        total = base + ((newsize + 2047) & ~2047)
        f.seek(0, 2)
        if f.tell() < total:
            f.write(b'\0' * (total - f.tell()))
        f.truncate(total)
        # PVD volume space size
        f.seek(16 * 2048 + 80); f.write(struct.pack('<I', total // 2048) + struct.pack('>I', total // 2048))
        # directory record of CROW.PAK: search USRDIR extent
        patch_dirrec(f, lba, size, newsize)
    if eboot is not None:
        el, es = iso_find(src_iso, '/PSP_GAME/SYSDIR/EBOOT.BIN')
        assert len(eboot) <= ((es + 2047) & ~2047), 'EBOOT grew past its sectors'
        f.seek(el * 2048); f.write(eboot)
        if len(eboot) != es:
            patch_dirrec(f, el, es, len(eboot))
    f.close()

def patch_dirrec(f, lba, oldsize, newsize):
    pat = struct.pack('<I', lba) + struct.pack('>I', lba) + struct.pack('<I', oldsize) + struct.pack('>I', oldsize)
    f.seek(0); hit = 0
    for sec in range(16, 400):
        f.seek(sec * 2048); d = f.read(2048)
        j = d.find(pat)
        if j >= 0:
            f.seek(sec * 2048 + j + 8); f.write(struct.pack('<I', newsize) + struct.pack('>I', newsize)); hit += 1
    assert hit >= 1, 'dir record not found'

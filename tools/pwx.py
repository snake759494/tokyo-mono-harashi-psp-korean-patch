"""PWX script container: u16 n, (2n-2) u16 offsets (units of 4 bytes), body.
Body is an ASCII command stream with inline Shift-JIS text."""
import struct, re

def parse(b):
    n = struct.unpack_from('<H', b)[0]
    cnt = max(2 * n - 2, 0)
    offs = list(struct.unpack_from('<%dH' % cnt, b, 2))
    hdr = 2 + cnt * 2
    return n, offs, hdr

DB = rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc])'
# a message: starts with double-byte char, ruby (l..(..)) or pm/pn; continues with those + 'r'
MSG = re.compile(rb'(?:' + DB + rb'|l' + DB + rb'+\(' + DB + rb'+\))'
                 rb'(?:' + DB + rb'|r|l' + DB + rb'+\(' + DB + rb'+\)|p[mnx])*')

def messages(body):
    """yield (start, end, bytes) of text runs in body (header skipped)"""
    n, offs, hdr = parse(body)
    for m in MSG.finditer(body, (hdr + 3) & ~3):
        s, e = m.start(), m.end()
        t = m.group()
        # trailing 'r' belongs to command stream? keep only if followed by text; trim
        while t.endswith(b'r') and not t.endswith(b'\x81r'):
            t = t[:-1]; e -= 1
        # avoid capturing 'pm'/'pn' that is just part of an ascii command (preceded by letter)
        if not re.search(DB, t):
            continue
        yield s, e, t

def rebuild(b, repl):
    """repl: dict start->(end,newbytes) over absolute file positions. Recomputes offsets,
    keeping each referenced position 4-aligned (pads with NUL after the preceding '_')."""
    n, offs, hdr = parse(b)
    hdr_al = (hdr + 3) & ~3
    refs = sorted(set(o * 4 for o in offs if o))
    # split into chunks at referenced positions
    cuts = [hdr_al] + refs + [len(b)]
    out = bytearray(b[:hdr_al])
    newpos = {}
    for i in range(len(cuts) - 1):
        a, z = cuts[i], cuts[i + 1]
        if i > 0:
            while len(out) % 4: out += b'\0'
            newpos[a] = len(out)
        chunk = b[a:z]
        # strip trailing pad (NUL/space) after final '_' when the next cut is a ref
        if i < len(cuts) - 2:
            k = len(chunk)
            while k > 0 and chunk[k - 1] in (0, 0x20): k -= 1
            if k > 0 and chunk[k - 1] == ord('_'):
                pad = chunk[k:]; chunk = chunk[:k]
            else:
                pad = b''
        else:
            pad = b''
        # apply replacements inside chunk
        res = bytearray(); p = 0
        for s in sorted(r for r in repl if a <= r < a + len(chunk)):
            e, nb = repl[s]
            res += chunk[p:s - a] + nb; p = e - a
        res += chunk[p:]
        out += res
        if pad:
            want = (len(out) + 3) & ~3
            out += bytes([pad[0]]) * (want - len(out))
    while len(out) % 4: out += b'\0'
    no = [newpos[o * 4] // 4 if o else 0 for o in offs]
    for o in no: assert o < 65536
    struct.pack_into('<%dH' % len(no), out, 2, *no)
    return bytes(out)

"""Extract table (CSVB), choice (ksf) and EBOOT strings into work/trans/src batches."""
import sys, os, re, glob, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zdv import unzdv
from csvb import CSVB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = ROOT + '/work/trans/src'
JP = re.compile(rb'[\x81-\x9f\xe0-\xef][\x40-\xfc]')
SKIP = {('dictionary.bin', 8)}  # kana reading used for index/sorting

def table_strings():
    out = {}; order = []
    for f in sorted(glob.glob(ROOT + '/work/tbl/*.bin')):
        name = os.path.basename(f)
        t = CSVB(open(f, 'rb').read())
        for r, c, x in t.strings():
            if (name, c) in SKIP or not JP.search(x): continue
            u = x.decode('cp932')
            if u not in out:
                out[u] = {'tbl': name[:-4], 'col': c}
                order.append(u)
    return order, out

KSF_RX = re.compile(rb'\x01((?:[\x81-\x9f\xe0-\xef][\x40-\xfc]|[\x20-\x7e])+)\x00')

def ksf_iter(b):
    for m in KSF_RX.finditer(b):
        s = m.group(1)
        if len(s) < 4 or not JP.search(s): continue
        slot = b[m.start() + 1:m.start() + 31]
        if slot[len(s):].strip(b'\0'): continue
        yield m.start() + 1, s

def ksf_strings():
    out = []
    for p in sorted(glob.glob(ROOT + '/work/pak/pw/*/*.ksf*')):
        b = open(p, 'rb').read()
        if p.endswith('.zdv'): b = unzdv(b)
        for o, s in ksf_iter(b):
            u = s.decode('cp932')
            if u not in out: out.append(u)
    return out

EB_RX = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]|[\x09\x0a\x20-\x7e])+\x00')

def eboot_strings(b):
    """(offset, bytes, capacity) for SJIS strings in the EBOOT data area"""
    res = []
    for m in EB_RX.finditer(b, 0x2a0000, 0x2e0000):
        s = m.group()[:-1]
        if b[m.start() - 1] != 0: continue
        if len(JP.findall(s)) < 2: continue
        try: u = s.decode('cp932')
        except UnicodeDecodeError: continue
        if not re.search('[ぁ-んァ-ヶ一-龠ー－]', u): continue
        if m.start() % 4: continue  # strings are 4-aligned in .rodata
        e = m.end()
        while e < len(b) and b[e] == 0 and (e % 4 or e == m.end()): e += 1
        res.append((m.start(), s, e - m.start() - 1))
    return res

if __name__ == '__main__':
    os.makedirs(SRC, exist_ok=True)
    order, meta = table_strings()
    batches = []; cur = []; n = 0
    for u in order:
        if cur and n > 12000:
            batches.append(cur); cur = []; n = 0
        cur.append(u); n += len(u)
    if cur: batches.append(cur)
    for bi, bt in enumerate(batches):
        out = []
        for j, u in enumerate(bt):
            lines = u.split('\n')
            out.append({'id': 't%02d_%04d' % (bi, j), 'tbl': meta[u]['tbl'], 'col': meta[u]['col'],
                        'maxline': max(len(l) for l in lines), 'ja': u})
        json.dump(out, open('%s/table_%02d.json' % (SRC, bi), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    print('tables', len(order), len(batches), [sum(len(u) for u in b) for b in batches])
    ks = ksf_strings()
    json.dump([{'id': 'c%04d' % i, 'ja': u, 'max': 15} for i, u in enumerate(ks)],
              open(SRC + '/choices.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    print('choices', len(ks))
    eb = open(ROOT + '/work/iso/EBOOT.dec', 'rb').read()
    es = eboot_strings(eb)
    json.dump([{'id': 'e%04d' % i, 'off': o, 'maxbytes': cap, 'ja': s.decode('cp932')} for i, (o, s, cap) in enumerate(es)],
              open(SRC + '/eboot.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    print('eboot', len(es), sum(len(s) for o, s, c in es))

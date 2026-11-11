"""Extract all translatable text into work/trans/src/*.json batches."""
import sys, os, re, glob, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zdv import unzdv
import pwx
from csvb import CSVB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = ROOT + '/work/trans/src'
NAME_RX = re.compile(r'^【([^】]*)】r?')

def load(p):
    b = open(p, 'rb').read()
    return unzdv(b) if p.endswith('.zdv') else b

def pw_files():
    fs = sorted(glob.glob(ROOT + '/work/pak/pw/*/*.pwx*'))
    order = {'in': 0, 'ms': 1, 'fn': 2, 'fd': 3, 'dg': 4, 'qs': 5}
    def key(p):
        n = os.path.basename(p).split('.')[0]
        return (int(n[2:4]) if n[2:4].isdigit() else 99, order.get(n[:2], 9), n)
    return sorted(fs, key=key)

def split_name(u):
    m = NAME_RX.match(u)
    if m: return m.group(1), u[m.end():]
    return None, u

def clean(u):
    """game markup -> translator view"""
    u = re.sub(r'l([^(r]+?)\(([^)]*)\)', lambda m: m.group(1) + '《' + m.group(2).replace('　', '') + '》', u)
    u = u.replace('px', '{PX}').replace('pm', '{PM}').replace('pn', '{PN}')
    u = re.sub(r'(?:(?<=[^\x00-\x7f])|(?<=\}))r|^r', '\n', u)
    return u

def script_items():
    seen = {}; items = []
    for p in pw_files():
        b = load(p)
        fn = os.path.basename(p).split('.')[0]
        for s, e, t in pwx.messages(b):
            u = t.decode('cp932')
            name, body = split_name(u)
            if body in seen: continue
            seen[body] = len(items)
            items.append({'k': body, 'file': fn, 'who': name})
    return items

if __name__ == '__main__':
    os.makedirs(SRC, exist_ok=True)
    items = script_items()
    # batches of ~11000 ja chars, split on file boundaries when possible
    batches = []; cur = []; n = 0
    for it in items:
        L = len(clean(it['k']))
        if cur and ((n > 11000 and cur[-1]['file'] != it['file']) or n > 14000):
            batches.append(cur); cur = []; n = 0
        cur.append(it); n += L
    if cur: batches.append(cur)
    keys = {}
    for bi, bt in enumerate(batches):
        out = []
        for j, it in enumerate(bt):
            kid = 's%02d_%04d' % (bi, j)
            keys[kid] = it['k']
            out.append({'id': kid, 'file': it['file'], 'who': it['who'] and clean(it['who']), 'ja': clean(it['k'])})
        json.dump(out, open('%s/script_%02d.json' % (SRC, bi), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    json.dump(keys, open(ROOT + '/work/trans/script_keys.json', 'w', encoding='utf8'), ensure_ascii=False)
    print(len(items), len(batches), [sum(len(clean(i['k'])) for i in b) for b in batches])

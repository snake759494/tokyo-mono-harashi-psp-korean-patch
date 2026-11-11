"""Validate a translated batch.  usage: python tools/check_ko.py script_05
Reads work/trans/txt/<name>.txt (source) and work/trans/ko/<name>*.txt (outputs, any number of parts)."""
import sys, os, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = re.compile(r'[぀-ヿ㐀-鿿豈-﫿]')
PH = re.compile(r'\{P[XMN]\}|%[0-9]*[ds]|\bp[mn]\b')

def load_src(name):
    src = {}
    for line in open(f'{ROOT}/work/trans/txt/{name}.txt', encoding='utf8'):
        line = line.rstrip('\n')
        if not line: continue
        parts = line.split('\t')
        src[parts[0]] = parts
    return src

def load_ko(name):
    ko = {}
    for f in sorted(glob.glob(f'{ROOT}/work/trans/ko/{name}.txt') + glob.glob(f'{ROOT}/work/trans/ko/{name}.p*.txt')):
        for line in open(f, encoding='utf8'):
            line = line.rstrip('\n').rstrip('\r')
            if not line.strip() or '\t' not in line: continue
            k, v = line.split('\t', 1)
            ko[k.strip()] = v
    return ko

def check(name, quiet=False):
    src = load_src(name); ko = load_ko(name)
    errs = []
    for k, parts in src.items():
        ja = parts[-1]
        if k not in ko:
            errs.append(f'{k} MISSING'); continue
        v = ko[k]
        if BAD.search(v):
            errs.append(f'{k} JP-CHAR: {v}')
        if sorted(PH.findall(ja)) != sorted(PH.findall(v)) and name != 'eboot':
            errs.append(f'{k} PLACEHOLDER {PH.findall(ja)} -> {PH.findall(v)}: {v}')
        if name == 'eboot':
            if sorted(re.findall(r'%[0-9]*[ds]', ja)) != sorted(re.findall(r'%[0-9]*[ds]', v)):
                errs.append(f'{k} FORMAT: {v}')
            cap = int(parts[1][8:])
            n = sum(1 if ord(c) < 0x80 else 2 for c in v.replace('\\n', '\n'))
            if n > cap: errs.append(f'{k} TOO LONG {n}>{cap} bytes: {v}')
        if name == 'choices' and len(v) > 15:
            errs.append(f'{k} TOO LONG {len(v)}>15: {v}')
        if name.startswith('table'):
            mx = int(parts[2][3:])
            for line in v.split('\\n'):
                w = sum(0.5 if c == ' ' else 1 for c in line)
                if w > max(mx, 4) + 1:
                    errs.append(f'{k} LINE {w}>{mx}: {line}')
    for k in ko:
        if k not in src: errs.append(f'{k} UNKNOWN ID')
    if not quiet:
        for e in errs[:80]: print(e)
        print(f'{name}: {len(ko)}/{len(src)} translated, {len(errs)} problems')
    return errs

if __name__ == '__main__':
    for n in sys.argv[1:]: check(n)

"""Draw Hangul into the game's IPK fonts, over kanji slots.
Hangul syllable i (KS X 1001 order, plus extras) -> i-th SJIS kanji code common to all fonts."""
import sys, os, json, struct
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ipk import IPK

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = {
    # name: (ttf, size, x_off, y_off, adv, inkh, gamma, threshold-style)
    'advfont14': (ROOT + '/SeoulHangangB.ttf', 13, 0, 0, 14, 14, 'aa'),
    'sysfont18': (ROOT + '/SeoulHangangEB.ttf', 17, 0, 0, 18, 18, 'aa'),
    'mobilefont': (ROOT + '/fonts_dl/Galmuri9.ttf', 10, 0, 0, 11, 12, 'bit'),
}
SPACE = 0x8140
SPACE_H = {'advfont14': 3}
SPACE_W = {'advfont14': 5, 'sysfont18': 6, 'mobilefont': 4}

def ks_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            out.append(bytes([hi, lo]).decode('euc-kr'))
    return out

def charmap(extra=()):
    """returns dict hangul->sjis code"""
    ks = [IPK(open(f'{ROOT}/work/font/{f}.ipk', 'rb').read()) for f in FONTS]
    sets = [set(e[0] for e in k.ent if e[0] >= 0x889f) for k in ks]
    com = sorted(set.intersection(*sets))
    chars = ks_hangul() + [c for c in extra if c not in ks_hangul()]
    assert len(chars) <= len(com), (len(chars), len(com))
    return {c: com[i] for i, c in enumerate(chars)}

_OFF = {}
def offsets(ttf, size, cw, chh):
    key = (ttf, size)
    if key not in _OFF:
        f = ImageFont.truetype(ttf, size)
        bb = [f.getbbox(c) for c in ks_hangul()]
        x0 = min(b[0] for b in bb); x1 = max(b[2] for b in bb)
        y0 = min(b[1] for b in bb); y1 = max(b[3] for b in bb)
        _OFF[key] = (f, (cw - (x1 - x0)) // 2 - x0, (chh - (y1 - y0)) // 2 - y0)
    return _OFF[key]

def render(ch, ttf, size, cw, chh, style):
    f, x, y = offsets(ttf, size, cw, chh)
    im = Image.new('L', (cw, chh), 0)
    d = ImageDraw.Draw(im)
    if style == 'bit':
        d.fontmode = '1'
    d.text((x, y), ch, font=f, fill=255)
    return im

def build(name, src, cmap):
    k = IPK(src)
    ttf, size, xo, yo, adv, inkh, style = FONTS[name]
    idx = {e[0]: i for i, e in enumerate(k.ent)}
    b = k.b
    for ch, code in cmap.items():
        i = idx[code]
        if ch == ' ':  # narrow space for vertical dialogue
            put(k, i, Image.new('L', (k.cw, k.ch), 0))
            struct.pack_into('<HBBH', b, 0x1c + 6 * i, code, SPACE_W[name], 4, 0); continue
        im = render(ch, ttf, size, k.cw, k.ch, style)
        put(k, i, im)
        struct.pack_into('<HBBH', b, 0x1c + 6 * i, code, adv, inkh, 0)
    i = idx[SPACE]
    e = list(struct.unpack_from('<HBBH', b, 0x1c + 6 * i))
    struct.pack_into('<HBBH', b, 0x1c + 6 * i, e[0], SPACE_W[name], SPACE_H.get(name, e[2]), e[3])
    if name in TRIM:
        b = trim(k, max(cmap.values()))
    return bytes(b)

# 글꼴은 표·대본과 같은 고정 영역에 올라간다. 한국어 표가 커진 만큼 뒤쪽 여유가 줄어
# 시험 후 오프닝 동영상 메모리 확보가 실패했다(던전으로 되돌아감, 실행마다 될 때도 있음).
# sysfont18 만 자른 v1.1 로는 여유가 모자라 세 글꼴 모두 한글 슬롯 뒤의 안 쓰는 한자
# 글리프를 잘라 낸다. (항목은 코드순 정렬, 앞쪽 색인은 그대로. build.py 가 표·대사에
# 잘린 코드가 남지 않았는지 검사한다)
TRIM = {'sysfont18', 'advfont14', 'mobilefont'}

def trim(k, last):
    b = k.b
    keep = max(i for i, e in enumerate(k.ent) if e[0] <= last) + 1
    pages = -(-keep // k.per)
    info_n = keep
    struct.pack_into('<H', b, 16, info_n)
    for i in range(keep, k.n):  # 남는 항목 자리는 0으로 (INFO 크기는 유지)
        b[0x1c + 6 * i:0x1c + 6 * i + 6] = b'\0' * 6
    img = k.img
    size = 16 + pages * k.psize
    struct.pack_into('<I', b, img + 4, size)
    out = b[:img + size]
    struct.pack_into('<I', out, 4, len(out))
    return out

def put(k, i, im):
    pg, c = divmod(i, k.per)
    x0 = (c % k.cols) * k.cw; y0 = (c // k.cols) * k.ch
    base = k.img + 16 + pg * k.psize
    px = im.load()
    for y in range(k.ch):
        for x in range(k.cw):
            v = (px[x, y] + 8) // 17
            if v > 15: v = 15
            X = x0 + x; o = base + (( y0 + y) * k.pw + X) // 2
            if X & 1: k.b[o] = (k.b[o] & 0x0F) | (v << 4)
            else: k.b[o] = (k.b[o] & 0xF0) | v

def used_extra():
    import glob
    ks = set(ks_hangul()); ex = set()
    for f in glob.glob(ROOT + '/work/trans/ko/*.txt'):
        for c in open(f, encoding='utf8').read():
            if '가' <= c <= '힣' and c not in ks: ex.add(c)
    return sorted(ex)

def main():
    cm = charmap(used_extra() + [' '])
    os.makedirs(ROOT + '/work/font_ko', exist_ok=True)
    json.dump({c: v for c, v in cm.items()}, open(ROOT + '/work/font_ko/charmap.json', 'w', encoding='utf8'), ensure_ascii=False)
    for n in FONTS:
        out = build(n, open(f'{ROOT}/work/font/{n}.ipk', 'rb').read(), cm)
        open(f'{ROOT}/work/font_ko/{n}.ipk', 'wb').write(out)
        print(n, len(out))

if __name__ == '__main__':
    main()

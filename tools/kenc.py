"""Korean text -> game Shift-JIS bytes using the hangul->kanji-slot charmap."""
import os, json, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cm = None

def cmap():
    global _cm
    if _cm is None:
        _cm = json.load(open(ROOT + '/work/font_ko/charmap.json', encoding='utf8'))
    return _cm

# half-width ascii punctuation -> full-width (ascii letters are script commands!)
FW = {c: chr(ord(c) + 0xFEE0) for c in '!?,.:;()/%+-=&#*0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz<>[]'}
FW.update({'_': '＿', '~': '～', '"': '”', "'": '’', '-': '－'})
SUBST = {'…': '…', '·': '・', '‘': '‘', '’': '’', '“': '“', '”': '”', '～': '～', '—': '―', '–': '－',
         '♪': '♪', '☆': '☆', '★': '★', '♥': '♥', '「': '「', '」': '」', '『': '『', '』': '』'}
TOK = re.compile(r'\{(PX|PM|PN)\}|\n|.', re.S)

def enc(s, space=b'\x81\x40', ascii_ok=False):
    """encode one text run. '\\n' -> 'r'; {PX}{PM}{PN} -> px/pm/pn.
    ascii_ok: keep printable ASCII as single bytes (EBOOT UI strings)."""
    cm = cmap(); out = bytearray()
    for m in TOK.finditer(s):
        t = m.group()
        if m.group(1):
            out += m.group(1).lower().encode(); continue
        if t == '\n': out += b'r'; continue
        if t == ' ': out += space; continue
        if ascii_ok and ' ' < t <= '~':
            out += t.encode(); continue
        if t in cm:
            c = cm[t]; out += bytes([c >> 8, c & 0xFF]); continue
        t = FW.get(t, SUBST.get(t, chr(ord(t) + 0xFEE0) if '!' <= t <= '~' else t))
        if t == '♥': t = '♪'
        try:
            b = t.encode('cp932')
        except UnicodeEncodeError:
            raise ValueError('cannot encode %r in %r' % (t, s))
        if len(b) != 2:
            raise ValueError('single-byte %r in %r' % (t, s))
        out += b
    return bytes(out)

def width(s, font='adv'):
    """pixel width of a line (adv14: full 14, space 5)"""
    w = 0
    for m in TOK.finditer(s):
        t = m.group()
        if m.group(1): w += 14 * 6; continue
        w += 5 if t == ' ' else 14
    return w

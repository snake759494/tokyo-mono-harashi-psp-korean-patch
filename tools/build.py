"""Full Korean build.  python tools/build.py [out.iso]"""
import sys, os, re, glob, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zdv import unzdv
import pwx, repack, kenc, fontgen
from csvb import CSVB
from extract_text import pw_files, split_name, load
from extract_misc import ksf_iter, SKIP, JP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = ROOT + '/Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Japan).iso'
OUT = ROOT + '/Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Korean).iso'
KO = ROOT + '/work/trans/ko'
TXT = ROOT + '/work/trans/txt'
COL = 14     # cells per vertical column (15 overflows the screen with full-height hangul)
COLS = 3     # columns per page
BS_N = chr(92) + 'n'

def read_pairs(pattern):
    d = {}
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding='utf8'):
            line = line.rstrip('\r\n')
            if '\t' in line:
                k, v = line.split('\t', 1); d[k.strip()] = v
    return d

def read_src(name):
    d = {}
    for line in open(f'{TXT}/{name}.txt', encoding='utf8'):
        line = line.rstrip('\n')
        if line: p = line.split('\t'); d[p[0]] = p
    return d

def ko_for(name):
    return read_pairs(f'{KO}/{name}.p*.txt') | read_pairs(f'{KO}/{name}.txt')

# ---------------------------------------------------------------- vertical wrap
NOSTART = set('。、，．！？…―」』）》～ー・!?,.)')
def wrap(text):
    """-> list of pages, each a list of column strings"""
    cols = []
    for para in text.split(BS_N):
        para = re.sub(r'\s+', ' ', para.strip())
        words = para.split(' ') if para else ['']
        cur = ''
        def cells(s): return len(re.sub(r'\{P[XMN]\}', 'XXXXX', s))
        for w in words:
            while cells(w) > COL:  # hard split long words
                room = COL - cells(cur) - (1 if cur else 0)
                if room <= 1:
                    cols.append(cur); cur = ''; continue
                cut = room
                while cut > 1 and w[cut] in NOSTART: cut -= 1
                cur = (cur + ' ' if cur else '') + w[:cut]; w = w[cut:]
                cols.append(cur); cur = ''
            if not cur: cur = w
            elif cells(cur) + 1 + cells(w) <= COL: cur += ' ' + w
            else:
                cols.append(cur); cur = w
        cols.append(cur)
    pages = [cols[i:i + COLS] for i in range(0, len(cols), COLS)]
    return pages

def enc_script(s):
    s = s.replace('.', '。').replace(',', '、').replace(' ', ' ')
    return kenc.enc(s)

# ---------------------------------------------------------------- script
def build_scripts(P, report):
    keys = json.load(open(ROOT + '/work/trans/script_keys.json', encoding='utf8'))
    names = read_pairs(f'{KO}/names.txt')
    body_ko = {}
    for f in sorted(glob.glob(f'{TXT}/script_*.txt')):
        n = os.path.basename(f)[:-4]
        ko = ko_for(n)
        for k in read_src(n):
            if k in ko: body_ko[keys[k]] = ko[k]
    miss = 0; pages_split = 0
    for p in pw_files():
        b = load(p)
        rep = {}
        for s, e, t in pwx.messages(b):
            u = t.decode('cp932')
            name, body = split_name(u)
            if body not in body_ko:
                miss += 1; continue
            ko = body_ko[body]
            nm = b''
            if name is not None:
                kn = names.get(name)
                if kn is None:
                    report.append('NAME? ' + name); kn = name
                nm = kenc.enc('【') + kenc.enc(kn) + kenc.enc('】') + b'r'
            title = b[s - 1:s] == b'{'
            if title:
                rep[s] = (e, enc_script(ko.replace(BS_N, '').replace(' ', ''))); continue
            pages = wrap(ko)
            if len(pages) > 1: pages_split += 1
            out = b''
            for i, pg in enumerate(pages):
                if i: out += b'wc' + nm
                else: out += nm
                out += b'r'.join(enc_script(c) for c in pg)
            rep[s] = (e, out)
        rel = os.path.relpath(p, ROOT + '/work/pak').replace(os.sep, '/').replace('.zdv', '')
        P[rel] = pwx.rebuild(b, rep)
    report.append(f'script: missing {miss}, multi-page {pages_split}')

def build_choices(P, report):
    ko = ko_for('choices'); src = read_src('choices')
    m = {src[k][-1]: v for k, v in ko.items() if k in src}
    n = 0
    for p in sorted(glob.glob(ROOT + '/work/pak/pw/*/*.ksf*')):
        b = bytearray(load(p)); ch = False
        for o, s in list(ksf_iter(bytes(b))):
            u = s.decode('cp932')
            if u in m:
                e = kenc.enc(m[u])
                if len(e) > 30: report.append('CHOICE LONG ' + m[u]); e = e[:30]
                b[o:o + 30] = e + b'\0' * (30 - len(e)); ch = True; n += 1
        if ch:
            rel = os.path.relpath(p, ROOT + '/work/pak').replace(os.sep, '/').replace('.zdv', '')
            P[rel] = bytes(b)
    report.append(f'choices: {n} slots')

# ---------------------------------------------------------------- tables
def enc_h(s):
    """horizontal UI text: keep real newlines"""
    return b'\n'.join(kenc.enc(x) for x in s.split(BS_N))

def build_tables(P, report):
    tr = {}
    for f in sorted(glob.glob(f'{TXT}/table_*.txt')):
        n = os.path.basename(f)[:-4]
        ko = ko_for(n); src = read_src(n)
        for k, parts in src.items():
            if k in ko: tr[parts[-1].replace(BS_N, '\n')] = ko[k]
    miss = set()
    for f in sorted(glob.glob(ROOT + '/work/tbl/*.bin')):
        name = os.path.basename(f)
        t = CSVB(open(f, 'rb').read())
        if not t.strcols: continue
        def fn(x, name=name):
            if not JP.search(x): return None
            u = x.decode('cp932')
            if u not in tr: miss.add(u); return None
            return enc_h(tr[u])
        # skip columns deliberately left in Japanese
        cols = t.strcols
        t.strcols = [c for c in cols if (name, c) not in SKIP]
        nb = t.rebuild(fn)
        if nb != t.b:
            P['app_init.pak/table/' + name] = nb
    report.append(f'tables: untranslated {len(miss)}')

# ---------------------------------------------------------------- eboot
def build_eboot(report):
    eb = bytearray(open(ROOT + '/work/iso/EBOOT.dec', 'rb').read())
    ko = ko_for('eboot'); src = read_src('eboot')
    import json as _j
    meta = {x['id']: x for x in _j.load(open(ROOT + '/work/trans/src/eboot.json', encoding='utf8'))}
    n = 0
    for k, v in ko.items():
        if k not in meta: continue
        m = meta[k]
        try:
            e = b'\n'.join(kenc.enc(x, space=b' ', ascii_ok=True) for x in v.split(BS_N))
        except ValueError as ex:
            report.append('EBOOT enc ' + str(ex)); continue
        if len(e) > m['maxbytes']:
            report.append(f'EBOOT long {k} {v}'); continue
        o = m['off']
        eb[o:o + m['maxbytes'] + 1] = e + b'\0' * (m['maxbytes'] + 1 - len(e))
        n += 1
    # name-entry keyboard: replace kana pages with hangul syllables
    syl = sorted(set(NAME_SYL.split()))
    kb = 0x2b1154
    slots = [i for i in range(82) if i != 23] + list(range(85, 167))
    assert len(syl) == len(slots), (len(syl), len(slots))
    import struct as _st
    for i, ch in zip(slots, syl):
        c = kenc.cmap()[ch]
        eb[kb + 4 * i:kb + 4 * i + 2] = bytes([c >> 8, c & 0xFF])
    for k, v in (('e0036', syl[0] + '～'), ('e0037', syl[81] + '～'), ('e0038', '영숫')):
        m = meta[k]; e = kenc.enc(v)
        eb[m['off']:m['off'] + m['maxbytes'] + 1] = e + bytes(1) * (m['maxbytes'] + 1 - len(e))
    eb[0x2d7b08:0x2d7b0c] = eb[0x2d7b10:0x2d7b14]  # default surname -> 시치다이 (reading slot)
    # one-kanji names (no room for hangul): point them at their translated reading string
    for q, d in ((0x2d7b34, 8), (0x2d7b80, 8), (0x2d7bfc, 8), (0x2d7c24, 8), (0x2d7cc4, 8), (0x2d7d64, 8),
                 (0x2d7db0, 8), (0x2d7dd8, 8), (0x2d7e00, 8), (0x2d7f68, 8),
                 (0x2d34a4, 4), (0x2d34c8, 4), (0x2d34ec, 4)):
        eb[q:q + 4] = eb[q + d:q + d + 4]
    eb[0x2b54b9:0x2b54bb] = kenc.enc('이')
    # honorific name tokens (pn君 / pm様 ...)
    for jp, kr in (('君', '군'), ('様', '님'), ('殿', '님')):
        a, b = b'pn' + jp.encode('cp932'), b'pm' + jp.encode('cp932')
        for t in (a, b):
            o = eb.find(t + b'\0', 0x2d3000)
            while 0 <= o < 0x2d4400:
                eb[o + 2:o + 4] = kenc.enc(kr); o = eb.find(t + b'\0', o + 4)
    # unlisted short strings: same byte length
    for o, s in ((0x2b4470, '%2d월%2d일'), (0x2b448c, '%2d월'), (0x2b4494, '%2d일'), (0x2b4360, '%s형'),
                 (0x2b0858, '%s를'), (0x2b5010, '%s를'), (0x2b5210, '엔'), (0x2b55d8, '엔'), (0x2b5214, '장'),
                 (0x2b5590, '춘'), (0x2b5594, '하'), (0x2b5598, '추'), (0x2b559c, '동'),
                 (0x2b55a8, '개'), (0x2b7ed4, '허'),
                 (0x2b7864, '무'), (0x2b7868, '사'), (0x2b786c, '곤'), (0x2b7870, '슬'), (0x2b7874, '열'),
                 (0x2b7878, '분'), (0x2b787c, '우'), (0x2b7880, '혐'), (0x2b7884, '기')):
        e = kenc.enc(s, ascii_ok=True)
        old = eb[o:eb.index(b'\0', o)]
        assert len(e) == len(old), (hex(o), e, old)
        eb[o:o + len(e)] = e
    report.append(f'eboot: {n} strings, keyboard {len(syl)} syllables')
    return bytes(eb)

NAME_SYL = '''가 강 개 건 결 경 고 광 구 국 군 권 귀 규 근 기 길 김 나 남 녀 노 다 단 담 대 덕 도 동 두 라 란 래 려 련 령 로 루 류 률 리 린
마 만 메 명 모 무 문 미 민 바 박 배 백 범 별 병 보 봉 부 비 빈 사 상 서 석 선 설 성 세 소 송 수 숙 순 쇼 슬 승 시 식 신 실 아 안 애 야 양
에 여 연 영 예 오 온 와 완 용 우 욱 운 웅 원 위 유 윤 은 의 이 인 일 자 장 재 전 정 제 조 종 주 준 쥬 즈 지 진 찬 창 채 천 철 초 츠 치 칠
카 케 코 쿄 쿠 큐 키 타 태 테 토 파 포 피 하 한 해 현 형 혜 호 홍 화 환 효 후 훈 희 히'''

def main(out=OUT):
    report = []
    P = {}
    fontgen.main()
    for f in ['advfont14', 'sysfont18', 'mobilefont']:
        P['app_init.pak/system/font/%s.ipk' % f] = open(f'{ROOT}/work/font_ko/{f}.ipk', 'rb').read()
    build_scripts(P, report)
    build_choices(P, report)
    build_tables(P, report)
    import imgko
    ip = imgko.patches(); P.update(ip); report.append(f'images: {len(ip)} gims')
    eb = build_eboot(report)
    import sign
    repack.build(ORIG, out, P, eboot=sign.sign(eb))
    print('\n'.join(report[-40:]))

if __name__ == '__main__':
    main(*sys.argv[1:])

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

# ---------------------------------------------------------------- speakers
# 대사의 【화자】 이름은 0x1e4540 이 실행 파일의 화자 표(seg1+0x13f48, 48명 x 10칸 포인터)와
# 바이트 단위로 똑같은지 비교해 화자 번호를 얻는다. 못 찾으면 -1 이 되고, 그 대사에 px(화자별
# 주인공 호칭)가 있으면 0x7ffe 번째 캐릭터 기록을 읽어 끝없는 문자열을 이어 붙이다가 메모리
# 밖에 써서 멈춘다(1화 점심시간 「부드러운 여학생 목소리」, GitHub 이슈 #1).
# 그래서 대본 화자 이름과 화자 표 문자열을 같은 인코딩·같은 글자로 맞춘다.
SPK_TABLE = 0x2c3b00 + 0x13f48
_SPK = None

def speaker_sync():
    """returns (eboot text overrides {id: ko}, pointer patches {file_off: vaddr},
    label overrides {jp: ko}, ids encoded like script text, report lines)"""
    global _SPK
    if _SPK is not None: return _SPK
    eb = open(ROOT + '/work/iso/EBOOT.dec', 'rb').read()
    rd = lambda v: struct.unpack_from('<I', eb, v + 0xc0)[0]
    cstr = lambda v: eb[v + 0xc0:eb.index(b'\0', v + 0xc0)]
    metas = json.load(open(ROOT + '/work/trans/src/eboot.json', encoding='utf8'))
    by_off = {x['off']: x for x in metas}
    ko = ko_for('eboot'); names = read_pairs(f'{KO}/names.txt')
    over, ptr, label, ids, rep, put = {}, {}, {}, set(), [], {}
    rows = []  # [(slot_vaddr, string_vaddr, jp_bytes)]
    for c in range(0x30):
        rows.append([(SPK_TABLE + c * 0x28 + 4 * k, rd(SPK_TABLE + c * 0x28 + 4 * k)) for k in range(10)])
        rows[-1] = [(s, p, cstr(p)) for s, p in rows[-1]]
    for c in rows:
        for s, p, j in c:
            m = by_off.get(p + 0xc0)
            if m: ids.add(m['id'])
    def kob(p, j):  # bytes the built EBOOT will hold at string p
        m = by_off.get(p + 0xc0)
        if m and m['id'] in over: return kenc.enc(over[m['id']])
        if m and m['id'] in ko: return kenc.enc(ko[m['id']].replace(BS_N, ''))
        return j
    for J, L in names.items():
        try: jb = J.encode('cp932')
        except UnicodeEncodeError: continue
        hit = [c for c in rows if any(j == jb for _, _, j in c)]
        if not hit: continue
        Lb = kenc.enc(L)
        if any(kob(p, j) == Lb for c in hit for _, p, j in c): continue
        s, p, _ = next(x for c in hit for x in c if x[2] == jb)
        m = by_off.get(p + 0xc0)
        if m and len(Lb) <= m['maxbytes']:
            over[m['id']] = L; rep.append(f'speaker eboot {m["id"]} {J} -> {L}'); continue
        a = spk_alloc(len(Lb) + 1, ids, over)
        if a is not None:  # 다른 문자열이 번역으로 짧아져 남은 빈자리에 새로 놓고 칸을 돌린다
            ptr[s] = a - 0xc0; put[a] = Lb + b'\0'
            rep.append(f'speaker moved {J} -> {L} @{a:x}'); continue
        label[J] = ko.get(m['id'], J) if m else J
        rep.append(f'speaker label {J}: {L} -> {label[J]}')
    _SPK = (over, ptr, label, ids, rep, put)
    return _SPK

_POOL = None
def spk_alloc(n, ids, over):
    """빈자리 할당: 번역이 원문보다 짧아 남은 문자열 꼬리(0으로 채워짐) 중 코드·데이터가
    가리키지 않는 곳만 쓴다. 반환값은 파일 오프셋."""
    global _POOL
    if _POOL is None:
        eb = open(ROOT + '/work/iso/EBOOT.dec', 'rb').read()
        refs = set()
        words = struct.unpack_from('<%dI' % ((len(eb) - 0xc0) // 4), eb, 0xc0)
        refs.update(words)
        for i, w in enumerate(words[:0x2a4a90 // 4]):  # lui/addiu 쌍이 만드는 주소
            if w >> 26 == 0x0f:
                r = (w >> 16) & 31; hi = (w & 0xffff) << 16
                for x in words[i + 1:i + 40]:
                    if (x >> 21) & 31 == r and x >> 26 in (0x09, 0x0d, 0x23, 0x21, 0x25, 0x20, 0x24, 0x28, 0x29, 0x2b):
                        lo = x & 0xffff
                        if x >> 26 != 0x0d and lo & 0x8000: lo -= 0x10000
                        refs.add((hi + lo) & 0xffffffff); break
        import bisect
        rs = sorted(v + 0xc0 for v in refs if 0x200000 <= v < 0x300000)
        ko = ko_for('eboot'); _POOL = []
        for x in json.load(open(ROOT + '/work/trans/src/eboot.json', encoding='utf8')):
            if x['id'] not in ko or x['id'] in ids or x['id'] in over: continue
            try: e = b'\n'.join(kenc.enc(t, space=b' ', ascii_ok=True) for t in ko[x['id']].split(BS_N))
            except ValueError: continue
            lo, hi = x['off'] + len(e) + 1, x['off'] + x['maxbytes'] + 1
            # 꼬리 안(과 바로 뒤)을 가리키는 참조가 있으면 안 쓴다
            i = bisect.bisect_left(rs, lo)
            if hi - lo >= 8 and not (i < len(rs) and rs[i] < hi):
                _POOL.append([lo, hi])
    for seg in _POOL:
        if seg[1] - seg[0] >= n:
            a = seg[0]; seg[0] += n; return a
    return None

# ---------------------------------------------------------------- script
def build_scripts(P, report):
    keys = json.load(open(ROOT + '/work/trans/script_keys.json', encoding='utf8'))
    names = read_pairs(f'{KO}/names.txt')
    names.update(speaker_sync()[2])
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
            # 시험 직후 장면(ms00_03): 이치루 대사의 px(화자별 호칭)를 그대로 두면 한국어판은
            # 오프닝 동영상으로 못 넘어가고 시험 던전으로 돌아간다(글꼴만 줄인 판 3/3 실패,
            # 아래 치환까지 한 판 3/3 성공). 게임 시작 직후라 이 시점 이치루의 호칭은 항상
            # 'pn군'(성+군)이므로 같은 결과가 나오는 토큰으로 바꿔 둔다.
            if os.path.basename(p).startswith('ms00_03.pwx') and name == 'いちる':
                out = out.replace(b'px', b'pn' + kenc.enc('군'))
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
    sp_over, sp_ptr, _, sp_ids, sp_rep, sp_put = speaker_sync()
    ko.update(sp_over); report.extend(sp_rep)
    for k, v in ko.items():
        if k not in meta: continue
        m = meta[k]
        try:
            if k in sp_ids:  # 화자 표 문자열은 대본 화자 이름과 같은 바이트여야 한다
                e = kenc.enc(v.replace(BS_N, ''))
            else:
                e = b'\n'.join(kenc.enc(x, space=b' ', ascii_ok=True) for x in v.split(BS_N))
        except ValueError as ex:
            report.append('EBOOT enc ' + str(ex)); continue
        if len(e) > m['maxbytes']:
            report.append(f'EBOOT long {k} {v}'); continue
        o = m['off']
        eb[o:o + m['maxbytes'] + 1] = e + b'\0' * (m['maxbytes'] + 1 - len(e))
        n += 1
    for a, v in sp_put.items():  # 빈자리에 놓은 화자 이름
        assert not any(eb[a:a + len(v)]), hex(a)
        eb[a:a + len(v)] = v
    for s, v in sp_ptr.items():  # 화자 표 칸을 그 문자열로 돌린다
        struct.pack_into('<I', eb, s + 0xc0, v)
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

def check_trimmed_glyphs(P, report):
    """sysfont18 은 한글 마지막 슬롯 뒤를 잘랐다. 표 문자열에 그 뒤 코드가 남으면 안 된다."""
    last = max(kenc.cmap().values()); bad = set()
    def scan(bs):
        i = 0
        while i < len(bs):
            c = bs[i]
            if (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc) and i + 1 < len(bs):
                code = (c << 8) | bs[i + 1]
                if code > last: bad.add(code)
                i += 2
            else: i += 1
    for k, v in P.items():
        if k.startswith('app_init.pak/table/'):
            t = CSVB(v)
            for r, c, s in t.strings():
                if (os.path.basename(k), c) in SKIP: continue
                scan(s)
        elif k.endswith('.pwx'):  # 대사 글꼴(advfont14)도 잘랐으므로 대사도 검사
            for s, e, t in pwx.messages(v): scan(t)
    if bad:
        raise SystemExit('trimmed glyph used: ' + ' '.join('%04X' % x for x in sorted(bad)[:40]))
    report.append('glyph trim check ok')

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
    check_trimmed_glyphs(P, report)
    import sign
    repack.build(ORIG, out, P, eboot=sign.sign(eb))
    print('\n'.join(report[-40:]))

if __name__ == '__main__':
    main(*sys.argv[1:])

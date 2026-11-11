"""Korean image patching.
specs: work/trans/img/*.json  each =
 {"src": "<expanded gim path>", "also": [same-image paths...],
  "ops": [ {"box":[x0,y0,x1,y1], "clear":"alpha0"|"fill"|[r,g,b,a]|"none",
            "text":"...", "font":"SeoulHangangEB", "size":16, "color":[r,g,b,a],
            "stroke":0, "stroke_color":[r,g,b,a], "vertical":false,
            "align":"center"|"left"|"right", "valign":"middle"|"top"|"bottom",
            "spacing":0, "shadow":[dx,dy,r,g,b,a], "bit":false } ...]}
 "fill" = paint box with the median colour of its 1-px border.
usage:
  python tools/imgko.py view <gim path> [scale] [x0 y0 x1 y1]   -> work/imgko/view.png (grid, checker)
  python tools/imgko.py render <spec.json|all>                  -> work/imgko/out/<name>.png + preview
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import gim
from tree import expand

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = ROOT + '/work/trans/img'
OUT = ROOT + '/work/imgko'
FONTS = {
    'SeoulHangangB': ROOT + '/SeoulHangangB.ttf', 'SeoulHangangEB': ROOT + '/SeoulHangangEB.ttf',
    'SeoulHangangM': ROOT + '/SeoulHangangM.ttf', 'SeoulHangangL': ROOT + '/SeoulHangangL.ttf',
    'NanumSquareNeoL': ROOT + '/NanumSquareNeo-aLt.ttf', 'NanumSquareNeoR': ROOT + '/NanumSquareNeo-bRg.ttf',
    'NanumSquareNeoB': ROOT + '/NanumSquareNeo-cBd.ttf', 'NanumSquareNeoEB': ROOT + '/NanumSquareNeo-dEb.ttf',
    'NanumSquareNeoH': ROOT + '/NanumSquareNeo-eHv.ttf',
    'Galmuri11': ROOT + '/fonts_dl/Galmuri11.ttf', 'Galmuri9': ROOT + '/fonts_dl/Galmuri9.ttf',
    'Galmuri7': ROOT + '/fonts_dl/Galmuri7.ttf',
}
_cache = {}

def load_gim(path):
    """expanded path (relative to work/pak) -> gim bytes"""
    if path in _cache: return _cache[path]
    if '#' in path:
        import znt
        zp, nm = path.split('#', 1)
        g = znt.get(load_gim(zp), nm); _cache[path] = g; return g
    parts = path.split('/')
    # find the on-disk file: longest prefix that exists (with or without .zdv)
    for i in range(len(parts), 0, -1):
        base = ROOT + '/work/pak/' + '/'.join(parts[:i])
        for cand in (base, base + '.zdv'):
            if os.path.isfile(cand):
                b = open(cand, 'rb').read()
                pre = '/'.join(parts[:i]) + ('.zdv' if cand.endswith('.zdv') else '')
                for q, d in expand(b, pre):
                    if q == path or (q.endswith('.znt') and q == path):
                        _cache[path] = d; return d
                raise KeyError(path)
    raise FileNotFoundError(path)

def checker(size, s=8):
    im = Image.new('RGBA', size, (90, 90, 90, 255)); d = ImageDraw.Draw(im)
    for y in range(0, size[1], s):
        for x in range(0, size[0], s):
            if (x // s + y // s) & 1: d.rectangle([x, y, x + s - 1, y + s - 1], fill=(60, 60, 60, 255))
    return im

def view(path, scale=2, box=None, dst=None):
    im = gim.decode(load_gim(path))
    if box: im = im.crop(box)
    ox, oy = (box[0], box[1]) if box else (0, 0)
    big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    bg = checker(big.size); bg.alpha_composite(big)
    d = ImageDraw.Draw(bg)
    step = 16 if max(im.size) <= 256 else 32
    for x in range(0, im.width, step):
        X = x * scale; d.line([X, 0, X, bg.height], fill=(0, 255, 255, 90))
        d.text((X + 1, 0), str(x + ox), fill=(0, 255, 0, 255))
    for y in range(0, im.height, step):
        Y = y * scale; d.line([0, Y, bg.width, Y], fill=(0, 255, 255, 90))
        d.text((0, Y + 1), str(y + oy), fill=(0, 255, 0, 255))
    dst = dst or OUT + '/view.png'
    os.makedirs(os.path.dirname(dst), exist_ok=True); bg.save(dst)
    return dst, im.size

def median_border(im, box):
    x0, y0, x1, y1 = box
    px = im.load(); cs = []
    for x in range(x0, x1):
        for y in (max(y0 - 1, 0), min(y1, im.height - 1)): cs.append(px[x, y])
    for y in range(y0, y1):
        for x in (max(x0 - 1, 0), min(x1, im.width - 1)): cs.append(px[x, y])
    return tuple(sorted(c[k] for c in cs)[len(cs) // 2] for k in range(4))

def draw_text(im, op):
    x0, y0, x1, y1 = op['box']
    text = op.get('text', '')
    if not text: return
    f = ImageFont.truetype(FONTS[op.get('font', 'SeoulHangangEB')], op.get('size', 16))
    col = tuple(op.get('color', [255, 255, 255, 255]))
    sw = op.get('stroke', 0); sc = tuple(op.get('stroke_color', [0, 0, 0, 255]))
    sp = op.get('spacing', 0)
    lines = text.split('\n')
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    if op.get('bit'): d.fontmode = '1'
    asc, desc = f.getmetrics()
    if op.get('vertical'):
        # columns right-to-left, one glyph per row
        cell_h = op.get('size', 16) + sp; cell_w = op.get('size', 16) + op.get('colgap', 2)
        cols = lines
        total_w = cell_w * len(cols) - op.get('colgap', 2)
        cx = (x0 + x1 + total_w) // 2 - cell_w // 2 if op.get('align', 'center') == 'center' else x1 - cell_w // 2
        for c in cols:
            th = cell_h * len(c) - sp
            va = op.get('valign', 'middle')
            y = y0 if va == 'top' else (y1 - th if va == 'bottom' else (y0 + y1 - th) // 2)
            for ch in c:
                bb = d.textbbox((0, 0), ch, font=f)
                gx = cx - (bb[0] + bb[2]) // 2; gy = y - bb[1] + (cell_h - sp - (bb[3] - bb[1])) // 2
                if ch in '、。，．': gx += op.get('size', 16) // 3; gy -= op.get('size', 16) // 3
                if ch in 'ー―－…～': ch_img(d, layer, ch, f, cx, y, cell_h - sp, col, sw, sc); y += cell_h; continue
                _t(d, (gx, gy), ch, f, col, sw, sc, op); y += cell_h
            cx -= cell_w
    else:
        lh = op.get('line_h', asc + desc + op.get('line_gap', 0))
        th = lh * len(lines)
        va = op.get('valign', 'middle')
        y = y0 if va == 'top' else (y1 - th if va == 'bottom' else (y0 + y1 - th) // 2)
        for ln in lines:
            w = d.textlength(ln, font=f) + sp * max(len(ln) - 1, 0)
            al = op.get('align', 'center')
            x = x0 if al == 'left' else (x1 - w if al == 'right' else (x0 + x1 - w) / 2)
            if sp:
                for ch in ln:
                    _t(d, (x, y), ch, f, col, sw, sc, op); x += d.textlength(ch, font=f) + sp
            else:
                _t(d, (x, y), ln, f, col, sw, sc, op)
            y += lh
    if op.get('gradient'):
        (r0, g0, b0), (r1, g1, b1) = op['gradient']
        gy0, gy1 = y0, y1
        a = layer.getchannel('A')
        grad = Image.new('RGBA', im.size)
        gd = ImageDraw.Draw(grad)
        for yy in range(im.height):
            t = min(max((yy - gy0) / max(gy1 - gy0, 1), 0), 1)
            gd.line([0, yy, im.width, yy], fill=(int(r0 + (r1 - r0) * t), int(g0 + (g1 - g0) * t), int(b0 + (b1 - b0) * t), 255))
        if sw:  # keep stroke colour where text fill is absent
            fillmask = Image.new('L', im.size, 0)
            ImageDraw.Draw(fillmask)
        grad.putalpha(a); layer = grad if not sw else _mix(layer, grad, col)
    if op.get('blur'):
        from PIL import ImageFilter
        layer = layer.filter(ImageFilter.GaussianBlur(op['blur']))
    if op.get('shadow'):
        dx, dy, *scol = op['shadow']
        a = layer.getchannel('A')
        sh = Image.new('RGBA', im.size, tuple(scol[:3]) + (0,)); sh.putalpha(a.point(lambda v: v * scol[3] // 255))
        im.alpha_composite(sh, (dx, dy))
    im.alpha_composite(layer)

def _mix(layer, grad, col):
    # replace pixels whose rgb equals fill colour with gradient
    import numpy as np
    L = np.array(layer); G = np.array(grad)
    m = (np.abs(L[..., :3].astype(int) - np.array(col[:3])).sum(-1) < 40)
    L[m, :3] = G[m, :3]
    return Image.fromarray(L)

def ch_img(d, layer, ch, f, cx, y, h, col, sw, sc):
    """rotate horizontal-line glyphs for vertical text"""
    g = Image.new('RGBA', (h * 2, h * 2), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    bb = gd.textbbox((0, 0), ch, font=f)
    gd.text((h - (bb[0] + bb[2]) // 2, h - (bb[1] + bb[3]) // 2), ch, font=f, fill=col, stroke_width=sw, stroke_fill=sc)
    g = g.rotate(-90)
    layer.alpha_composite(g, (int(cx - h), int(y + h // 2 - h)))

def _t(d, xy, s, f, col, sw, sc, op):
    d.text(xy, s, font=f, fill=col, stroke_width=sw, stroke_fill=sc)

def apply_spec(sp):
    im = gim.decode(load_gim(sp['src'])).convert('RGBA')
    if sp.get('png'):
        new = Image.open(ROOT + '/' + sp['png']).convert('RGBA')
        im.paste(new, (0, 0))
    for op in sp.get('ops', []):
        x0, y0, x1, y1 = op['box']
        cl = op.get('clear', 'alpha0')
        if cl == 'alpha0':
            im.paste((0, 0, 0, 0), (x0, y0, x1, y1))
        elif cl == 'fill':
            im.paste(median_border(im, op['box']), (x0, y0, x1, y1))
        elif isinstance(cl, list):
            im.paste(tuple(cl), (x0, y0, x1, y1))
        for cb in op.get('clear_boxes', []):
            im.paste(tuple(op.get('clear_color', [0, 0, 0, 0])), tuple(cb))
        draw_text(im, op)
    return im

def name_of(spec_path):
    return os.path.splitext(os.path.basename(spec_path))[0]

def render(which='all'):
    files = sorted(glob.glob(SPECS + '/*.json')) if which == 'all' else [which]
    os.makedirs(OUT + '/out', exist_ok=True)
    res = {}
    for fp in files:
        sp = json.load(open(fp, encoding='utf8'))
        im = apply_spec(sp)
        n = name_of(fp)
        im.save(OUT + '/out/' + n + '.png')
        # preview: original | patched, on checker, x2
        orig = gim.decode(load_gim(sp['src']))
        pv = Image.new('RGBA', (im.width * 2 + 8, im.height), (255, 0, 255, 255))
        a = checker(orig.size); a.alpha_composite(orig); b_ = checker(im.size); b_.alpha_composite(im)
        pv.paste(a, (0, 0)); pv.paste(b_, (im.width + 8, 0))
        sc = 2 if im.width <= 256 else 1
        pv = pv.resize((pv.width * sc, pv.height * sc), Image.NEAREST)
        pv.save(OUT + '/out/' + n + '_preview.png')
        res[n] = (sp, im)
    return res

def all_gims():
    import hashlib
    idx = {}
    for r, ds, fs in os.walk(ROOT + '/work/pak'):
        for f in fs:
            p = os.path.join(r, f).replace(os.sep, '/')
            for q, d in expand(open(p, 'rb').read(), p):
                rel = q.split('/work/pak/', 1)[1]
                if q.endswith('.gim'):
                    _cache[rel] = d
                    idx.setdefault(hashlib.md5(d).hexdigest(), []).append(rel)
                elif q.endswith('.znt'):
                    import znt
                    _cache[rel] = d
                    for nm, a, e in znt.entries(d):
                        idx.setdefault(hashlib.md5(d[a:e]).hexdigest(), []).append(rel + '#' + nm)
    return idx

def patches():
    """-> {expanded path: new gim bytes} for build.py (identical copies patched too)"""
    import hashlib
    idx = all_gims()
    P = {}
    for n, (sp, im) in render('all').items():
        h = hashlib.md5(load_gim(sp['src'])).hexdigest()
        for path in set(idx.get(h, []) + [sp['src']] + sp.get('also', [])):
            P[path] = gim.encode(load_gim(path), im)
    # fold znt textures into their container
    import znt
    out = {}
    for path, g in P.items():
        if '#' in path:
            zp, nm = path.split('#', 1)
            cur = out.get(zp) or load_gim(zp)
            out[zp] = znt.put(cur, nm, g)
        else:
            out[path] = g
    return out

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'view':
        a = sys.argv[2:]
        box = [int(v) for v in a[2:6]] if len(a) >= 6 else None
        print(view(a[0], int(a[1]) if len(a) > 1 else 2, box))
    elif c == 'render':
        r = render(sys.argv[2] if len(sys.argv) > 2 else 'all')
        print('rendered', len(r), [OUT + '/out/' + k + '_preview.png' for k in r])

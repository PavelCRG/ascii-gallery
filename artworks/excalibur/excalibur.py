import argparse
import math
import os
import string
import subprocess

import numpy as np

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

VW, VH = 1080, 1920
LAYOUT = os.environ.get("CLIP_LAYOUT", "full")
WIDE = os.environ.get("CLIP_WIDE", "0") == "1"
CONTENT_W, CONTENT_H = ((1040, 585) if WIDE else (1040, 1100)) if LAYOUT == "ide" else (VW, VH)
WIN_X, WIN_Y = 20, (700 if WIDE else 470)
BG = np.array([12, 12, 16], np.float32)
CHARS = string.ascii_letters + string.digits + "#%&@$*+=<>/\\?!;:.,-"
FONT = int(os.environ.get("CLIP_FONT", "13"))
GAIN = float(os.environ.get("CLIP_GAIN", "1.35"))
SAT = float(os.environ.get("CLIP_SAT", "1.6"))
T_ASM = -1.0
ZOOM0, T_ZHOLD, T_ZOOM = 9.0, 0.35, 3.0

rng = np.random.default_rng(3)


def build_atlas(size):
    font = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", size)
    cw = int(round(font.getlength("M")))
    asc, desc = font.getmetrics()
    ch = asc + desc + 1
    a = np.zeros((len(CHARS), ch, cw), np.float32)
    for i, c in enumerate(CHARS):
        im = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
        a[i] = np.clip(np.asarray(im, np.float32) / 255 * 1.25, 0, 1) ** 0.75
    return a, cw, ch, np.argsort(a.mean(axis=(1, 2)))


ATLAS, CW, CH, ORDER = build_atlas(FONT)
COLS, ROWS = CONTENT_W // CW, CONTENT_H // CH
RR, CC = np.meshgrid(np.arange(ROWS), np.arange(COLS), indexing="ij")

_ang = np.arctan2(RR - ROWS / 2, (CC - COLS / 2) * CW / CH) + rng.normal(0, 0.5, RR.shape)
ASM_D = (0.6 + 0.6 * rng.random(RR.shape)) * max(COLS, ROWS * CH / CW)
ASM_A = _ang
ASM_S = rng.uniform(0.0, 0.6, RR.shape)
ASM_T = 0.9


def sstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


class Glyphs:

    def __init__(self):
        self.noise = rng.normal(0, 0.1, (ROWS, COLS))

    def step(self):
        m = rng.random((ROWS, COLS)) < 0.06
        self.noise[m] = rng.normal(0, 0.1, m.sum())

    def pick(self, lum):
        pos = np.clip(lum * 0.8 + 0.2 + self.noise, 0, 0.999)
        return ORDER[(pos * len(ORDER)).astype(int)]


def prep(img):
    w, h = img.size
    cw = int(h * CONTENT_W / CONTENT_H)
    img = img.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    img = ImageEnhance.Color(img).enhance(SAT)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    small = np.asarray(img.resize((COLS, ROWS), Image.LANCZOS), np.float32)
    lum = small @ np.array([0.299, 0.587, 0.114], np.float32) / 255
    return small, lum


_atl = {}


def atlas_k(k):
    if k not in _atl:
        font = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", FONT * k)
        a = np.zeros((len(CHARS), CH * k, CW * k), np.float32)
        for i, c in enumerate(CHARS):
            im = Image.new("L", (CW * k, CH * k), 0)
            ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
            a[i] = np.clip(np.asarray(im, np.float32) / 255 * 1.25, 0, 1) ** 0.75
        _atl[k] = a
    return _atl[k]


def zoom_at(t):
    if t >= T_ZOOM:
        return 1.0
    e = sstep(T_ZHOLD, T_ZOOM, t)
    return float(ZOOM0 ** (1 - e))


def compose_zoom(col, idx, has, z, fx=0.5, fy=0.42, glow=0.35):
    zi = int(math.ceil(z - 1e-6))
    A = atlas_k(zi)
    cw, ch = CW * zi, CH * zi
    cx, cy = COLS * fx, ROWS * fy
    wc, hc = CONTENT_W / (CW * z), CONTENT_H / (CH * z)
    c0, c1 = max(0, int(cx - wc / 2) - 1), min(COLS, int(math.ceil(cx + wc / 2)) + 1)
    r0, r1 = max(0, int(cy - hc / 2) - 1), min(ROWS, int(math.ceil(cy + hc / 2)) + 1)
    g = A[idx[r0:r1, c0:c1]] * has[r0:r1, c0:c1, None, None]
    cc = col[r0:r1, c0:c1]
    out = BG + g[..., None] * (cc[:, :, None, None, :] - BG)
    out = out.transpose(0, 2, 1, 3, 4).reshape((r1 - r0) * ch, (c1 - c0) * cw, 3)
    k = zi / z
    M = np.float32([[k, 0, (cx - c0) * cw - CONTENT_W / 2 * k], [0, k, (cy - r0) * ch - CONTENT_H / 2 * k]])
    res = cv2.warpAffine(out.astype(np.float32), M, (CONTENT_W, CONTENT_H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=tuple(float(v) for v in BG))
    gl = cv2.GaussianBlur(np.clip(res, 0, 255), (0, 0), 4 * min(z, 4) ** 0.5)
    return np.clip(res + glow * gl, 0, 255).astype(np.uint8)


def compose(col, idx, has, tint=0.0, glow=0.35):
    g = ATLAS[idx] * has[:, :, None, None]
    base = BG + tint * col
    out = base[:, :, None, None, :] + g[..., None] * (col[:, :, None, None, :] - base[:, :, None, None, :])
    out = out.transpose(0, 2, 1, 3, 4).reshape(ROWS * CH, COLS * CW, 3)
    o8 = np.clip(out, 0, 255).astype(np.uint8)
    gl = np.asarray(Image.fromarray(o8).filter(ImageFilter.GaussianBlur(4)), np.float32)
    res = np.clip(out + glow * gl, 0, 255).astype(np.uint8)
    canvas = np.zeros((CONTENT_H, CONTENT_W, 3), np.uint8)
    canvas[:] = BG.astype(np.uint8)
    y0, x0 = (CONTENT_H - res.shape[0]) // 2, (CONTENT_W - res.shape[1]) // 2
    canvas[y0:y0 + res.shape[0], x0:x0 + res.shape[1]] = res
    return canvas


def load_cuts(path="cuts.txt", gap=0.35):
    if not os.path.exists(path):
        return np.array([])
    out = []
    for line in open(path):
        try:
            c = float(line)
        except ValueError:
            continue
        if not out or c - out[-1] >= gap:
            out.append(c)
    return np.array(out)


CUTS = load_cuts()

import cv2

SUBS = np.load("subs.npz") if os.path.exists("subs.npz") else None
BIG = [("ex", "EX.."), ("calibur", "-CALIBUR!")]


def erase_subs(img, t):
    if SUBS is None:
        return img
    x0, y0, x1, y1 = SUBS["box"]
    for name in ("destroy", "ex", "calibur"):
        a, b = SUBS[name + "_t"]
        if a - 0.05 <= t <= b + 0.05:
            arr = np.asarray(img).copy()
            m = cv2.dilate(SUBS[name].astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
            pad = 12
            roi = arr[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
            mm = np.zeros(roi.shape[:2], np.uint8)
            mm[pad:-pad, pad:-pad] = m
            arr[y0 - pad:y1 + pad, x0 - pad:x1 + pad] = cv2.inpaint(roi, mm, 6, cv2.INPAINT_TELEA)
            img = Image.fromarray(arr)
    return img


_big = {}


def big_text_cells(text, scale):
    key = (text, round(scale, 2))
    if key not in _big:
        f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 12)
        im = Image.new("L", (300, 24), 0)
        d, x = ImageDraw.Draw(im), 2
        d.fontmode = "1"
        for c in text:
            d.text((x, 4), c, font=f, fill=255)
            x += f.getlength(c) + 1
        a = np.asarray(im) > 0
        r, c = np.nonzero(a.any(1))[0], np.nonzero(a.any(0))[0]
        a = a[r[0]:r[-1] + 1, c[0]:c[-1] + 1].astype(np.float32)
        a = np.repeat(a, 2, axis=1)
        if scale > 1.001:
            a = cv2.resize(a, (int(a.shape[1] * scale), int(a.shape[0] * scale)), interpolation=cv2.INTER_NEAREST)
        _big[key] = a
    return _big[key]


def draw_big(col, idx, has, t):
    if SUBS is None:
        return col, idx, has
    for name, text in BIG:
        a, b = SUBS[name + "_t"]
        if not (a <= t <= b):
            continue
        u = t - a
        scale = 1.0 + 0.35 * max(0.0, 1 - u / 0.12)
        fade = min(1.0, (b - t) / 0.1)
        cov = big_text_cells(text, scale)
        th, tw = cov.shape
        r0 = int(ROWS * 0.78 - th / 2)
        c0 = (COLS - tw) // 2
        R0, C0 = max(r0, 0), max(c0, 0)
        R1, C1 = min(r0 + th, ROWS), min(c0 + tw, COLS)
        sub = cov[R0 - r0:R1 - r0, C0 - c0:C1 - c0]
        inside = sub > 0.4
        ring = (cv2.dilate(inside.astype(np.uint8), np.ones((3, 5), np.uint8)) > 0) & ~inside
        cr, cc_ = col[R0:R1, C0:C1], idx[R0:R1, C0:C1]
        cr[ring] = cr[ring] * 0.08
        cc_[ring] = CHARS.index(".")
        rr, ccn = np.nonzero(inside)
        cc_[rr, ccn] = np.where((rr + ccn) % 2, CHARS.index("@"), CHARS.index("#"))
        k = np.clip((np.arange(R1 - R0)[:, None] / max(1, R1 - R0 - 1)), 0, 1)
        grad = np.array([255, 225, 70]) * (1 - k[..., None]) + np.array([255, 120, 20]) * k[..., None]
        flash = 1 + 0.6 * max(0.0, 1 - u / 0.15)
        cr[inside] = (grad.repeat(C1 - C0, 1)[inside] * flash * fade)
        has[R0:R1, C0:C1] |= inside
    return col, idx, has


def frame(img, t, glyphs):
    img = erase_subs(img, t)
    col, lum = prep(img)
    idx = glyphs.pick(lum)
    has = np.ones((ROWS, COLS), bool)
    g = GAIN
    col = col * g / (1 + (g - 1) * col / 255)

    if len(CUTS):
        k = np.searchsorted(CUTS, t, side="right") - 1
        age = t - CUTS[k] if k >= 0 else 9
        if 0 <= age < 0.1:
            p = 1 - age / 0.1
            scr = rng.random((ROWS, COLS)) < 0.55 * p
            idx = np.where(scr, rng.integers(0, len(CHARS), (ROWS, COLS)), idx)
            shift = (rng.normal(0, 6, ROWS) * p * (rng.random(ROWS) < 0.35)).astype(int)
            for r in np.nonzero(shift)[0]:
                idx[r] = np.roll(idx[r], shift[r])
                col[r] = np.roll(col[r], shift[r], axis=0)
            col = col * (1 + 0.45 * p)
            sh = int(3 * p) + 1
            col[:, :, 0] = np.roll(col[:, :, 0], sh, axis=1)
            col[:, :, 2] = np.roll(col[:, :, 2], -sh, axis=1)

    col, idx, has = draw_big(col, idx, has, t)

    if t < T_ASM + 0.3:
        ncol = np.zeros_like(col)
        nidx = np.zeros_like(idx)
        nhas = np.zeros_like(has)
        dash = CHARS.index("-")
        for j in range(5, -1, -1):
            tj = t - 0.035 * j
            v = np.clip((tj - ASM_S) / ASM_T, 0, 1)
            e = 1 - (1 - v) ** 3
            off = (1 - e) * ASM_D
            a = ASM_A + (1 - e) * 1.4
            r = np.round(RR + off * np.sin(a) * CW / CH).astype(int)
            c = np.round(CC + off * np.cos(a)).astype(int)
            ok = (r >= 0) & (r < ROWS) & (c >= 0) & (c < COLS) & (v > 0)
            if j:
                ok &= v < 1
                k = 0.55 * 0.72 ** j
                ncol[r[ok], c[ok]] = col[ok] * k
                nidx[r[ok], c[ok]] = dash if j > 2 else idx[ok]
            else:
                bright = (1 - e) * 0.8 + 1.0
                ncol[r[ok], c[ok]] = col[ok] * bright[ok][:, None]
                nidx[r[ok], c[ok]] = idx[ok]
            nhas[r[ok], c[ok]] = True
        col, idx, has = ncol, nidx, nhas
    z = zoom_at(t)
    if z > 1.001:
        return compose_zoom(col, idx, has, z)
    return compose(col, idx, has)


_ide = {}


def clean_source():
    import io
    import tokenize
    src = open(__file__, encoding="utf8").read()
    lines = src.splitlines()
    cut, drop, prev = {}, set(), tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            cut[tok.start[0] - 1] = tok.start[1]
        elif tok.type == tokenize.STRING and prev in (tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT):
            drop.update(range(tok.start[0] - 1, tok.end[0]))
        if tok.type not in (tokenize.COMMENT, tokenize.NL):
            prev = tok.type
    out = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        if i in cut:
            line = line[:cut[i]].rstrip()
            if not line.strip():
                continue
        out.append(line)
    return out


def ide_layers():
    import re
    if _ide:
        return _ide
    kw = {"def", "return", "import", "from", "for", "in", "if", "else", "elif", "while", "class", "and", "or",
          "not", "None", "True", "False", "lambda", "with", "as"}
    tok_re = re.compile(r'("[^"]*"|\'[^\']*\')|(\b\d+\.?\d*\b)|([A-Za-z_]\w*)|(.)')
    lines = clean_source()
    st = next(i for i, l in enumerate(lines) if l.startswith("def frame("))
    lines = lines[max(0, st - 20):st + 70]
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 21)
    fb = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 21)
    seg = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
    code = Image.new("RGB", (VW, 27 * len(lines) + 40), (43, 43, 43))
    d = ImageDraw.Draw(code)
    d.rectangle((0, 0, 58, code.height), fill=(49, 51, 53))
    for i, line in enumerate(lines):
        y = 10 + i * 27
        d.text((52, y), str(st - 19 + i), font=f, fill=(96, 99, 102), anchor="ra")
        x, prev = 72, ""
        for m in tok_re.finditer(line):
            tok = m.group(0)
            ft = f
            if m.group(1):
                c = (106, 135, 89)
            elif m.group(2):
                c = (104, 151, 187)
            elif m.group(3) and tok in kw:
                c, ft = (204, 120, 50), fb
            elif m.group(3) and prev == "def":
                c = (255, 198, 109)
            else:
                c = (169, 183, 198)
            d.text((x, y), tok, font=ft, fill=c)
            x += f.getlength(tok)
            if m.group(3):
                prev = tok
            if x > VW:
                break
    top = Image.new("RGB", (VW, 64), (60, 63, 65))
    dt = ImageDraw.Draw(top)
    dt.rectangle((0, 0, 240, 64), fill=(43, 43, 43))
    dt.rectangle((0, 60, 240, 64), fill=(74, 136, 199))
    dt.text((24, 18), "excalibur.py", font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24), fill=(200, 200, 200))
    run = Image.new("RGB", (VW, 250), (43, 43, 43))
    dr = ImageDraw.Draw(run)
    dr.rectangle((0, 0, VW, 46), fill=(60, 63, 65))
    dr.text((20, 9), "Run:   excalibur", font=seg, fill=(200, 200, 200))
    dr.text((20, 66), "> python excalibur.py saber.mp4", font=f, fill=(169, 183, 198))
    dr.text((20, 100), f"{COLS}x{ROWS} chars  |  {len(CHARS)} glyphs  |  60 fps", font=f, fill=(106, 135, 89))
    title = Image.new("RGB", (CONTENT_W, 36), (243, 243, 243))
    dti = ImageDraw.Draw(title)
    dti.text((40, 7), "excalibur", font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18), fill=(20, 20, 20))
    dti.ellipse((12, 10, 28, 26), outline=(70, 120, 200), width=3)
    sym = ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 18)
    for i, ch_ in enumerate(("—", "☐", "✕")):
        dti.text((CONTENT_W - 140 + i * 46, 6), ch_, font=sym, fill=(30, 30, 30))
    shadow = Image.new("L", (CONTENT_W + 80, 36 + CONTENT_H + 80), 0)
    ImageDraw.Draw(shadow).rectangle((40, 40, 40 + CONTENT_W, 40 + 36 + CONTENT_H), fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    _ide.update(code=code, top=top, run=run, title=title, shadow=shadow)
    return _ide


def to_ide(content, t, dur):
    import math
    e = ide_layers()
    out = Image.new("RGB", (VW, VH), (43, 43, 43))
    scroll = int(320 * (1 - math.cos(2 * math.pi * t / dur)) / 2)
    out.paste(e["code"].crop((0, scroll, VW, scroll + VH - 64 - 250)), (0, 64))
    out.paste(e["top"], (0, 0))
    out.paste(e["run"], (0, VH - 250))
    out.paste(Image.new("RGB", e["shadow"].size, (0, 0, 0)), (WIN_X - 40, WIN_Y - 40 + 6), e["shadow"])
    out.paste(e["title"], (WIN_X, WIN_Y))
    out.paste(Image.fromarray(content), (WIN_X, WIN_Y + 36))
    return np.asarray(out)


def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip().split(",")
    n, d = o[2].split("/")
    return int(o[0]), int(o[1]), float(n) / float(d), o[2]


def grab(path, t):
    w, h, _, _ = probe(path)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.fromarray(np.frombuffer(raw, np.uint8)[: w * h * 3].reshape(h, w, 3))


def export(src, out, to):
    w, h, fps, rate = probe(src)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-t", str(to), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
                            "-r", rate, "-i", "-", "-ss", "0", "-t", str(to), "-i", src, "-map", "0:v", "-map", "1:a",
                            "-af", f"afade=t=out:st={to - 0.25:.2f}:d=0.25",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    glyphs = Glyphs()
    size = w * h * 3
    i = 0
    while True:
        raw = dec.stdout.read(size)
        if len(raw) < size:
            break
        img = Image.fromarray(np.frombuffer(raw, np.uint8).reshape(h, w, 3))
        fr = frame(img, i / fps, glyphs)
        if LAYOUT == "ide":
            fr = to_ide(fr, i / fps, to)
        enc.stdin.write(fr.tobytes())
        glyphs.step()
        i += 1
        if i % 48 == 0:
            print(i, flush=True)
    enc.stdin.close()
    enc.wait()
    print("done:", out, i, "frames")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--export")
    ap.add_argument("--to", type=float, default=36.0)
    ap.add_argument("--out", default="stills")
    a = ap.parse_args()
    if a.still:
        os.makedirs(a.out, exist_ok=True)
        g = Glyphs()
        for s in a.still:
            fr = frame(grab(a.src, s), s, g)
            if LAYOUT == "ide":
                fr = to_ide(fr, s, a.to)
            Image.fromarray(fr).save(f"{a.out}/t{s:05.2f}.png")
        print("ok", COLS, "x", ROWS, "cuts:", len(CUTS))
    elif a.export:
        export(a.src, a.export, a.to)

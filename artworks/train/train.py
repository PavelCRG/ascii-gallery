import argparse
import math
import os
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FPS = 60
DURATION = 24.0
VW, VH = 1080, 1920
BG = np.array([14, 14, 18], np.float32)
FONT = 9
BEAT = 0.75
DROP = 9.0
AUDIO_START = 15.055
ZOOM0, T_ZOOM = 9.0, 2.4
CHARS = "".join(chr(c) for c in range(33, 127))

FONTS = {
    "mono_b": ["C:/Windows/Fonts/consolab.ttf", "/System/Library/Fonts/Menlo.ttc", "DejaVuSansMono-Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"],
    "mono": ["C:/Windows/Fonts/consola.ttf", "/System/Library/Fonts/Menlo.ttc", "DejaVuSansMono.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
    "ui": ["C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Helvetica.ttc", "DejaVuSans.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "sym": ["C:/Windows/Fonts/seguisym.ttf", "/System/Library/Fonts/Apple Symbols.ttf", "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def load_font(kind, size):
    for name in FONTS[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def sstep(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)


_atlas = {}


def atlas(size):
    if size not in _atlas:
        font = load_font("mono_b", size)
        cw = max(1, int(round(font.getlength("M"))))
        asc, desc = font.getmetrics()
        ch = asc + desc - max(1, size // 9)
        at = np.zeros((len(CHARS) + 1, ch, cw), np.float32)
        for i, c in enumerate(CHARS):
            im = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
            at[i + 1] = np.clip(np.asarray(im, np.float32) / 255 * 1.25, 0, 1) ** 0.75
        _atlas[size] = (at, cw, ch)
    return _atlas[size]


AT, CW, CH = atlas(FONT)
IMG_W = 1080
IMG_H = 810
COLS, ROWS = IMG_W // CW, IMG_H // CH
ORDER = np.argsort(AT[1:].mean(axis=(1, 2))) + 1
rng = np.random.default_rng(11)
NOISE = rng.normal(0, 0.1, (ROWS, COLS))
SHIM = rng.random((ROWS, COLS))


SS = 2
GW, GH = COLS * SS, ROWS * SS
ASP = IMG_W / IMG_H
PX = ((np.arange(GW) + 0.5) / GW * ASP)[None, :] * np.ones((GH, 1), np.float32)
PY = ((np.arange(GH) + 0.5) / GH)[:, None] * np.ones((1, GW), np.float32)
HORIZON = 0.64
L_GRASS, V_GRASS = 0.75, 4.5
L_HILL, V_HILL = 4.0, 4.0 / DURATION
L_TREE, V_TREE = 2.0, 0.5
POLE, V_POLE = 0.9, 2.4
L_GRND, V_GRND = 1.5, 3.0
T_TRAIN0, T_TRAIN1 = DROP - 0.05, DROP + 1.6
STARS = list(zip(rng.uniform(0, ASP, 110), rng.uniform(0.0, 1.0, 110) ** 1.3 * 0.42,
                 rng.uniform(0.3, 1.0, 110), rng.uniform(0, 6.3, 110)))
VILL = rng.uniform(0, L_TREE, 14)
VILL_H = rng.uniform(0.0, 0.03, 14)
VILL_P = rng.uniform(0, 6.3, 14)


def mix(a, b, k):
    return a + (np.asarray(b, np.float32) - a) * np.asarray(k, np.float32)[..., None]


def periodic(x, period, terms):
    w = 2 * np.pi / period
    return sum(amp * np.sin(w * k * x + ph) for k, amp, ph in terms)


def pulse(t):
    if t < DROP:
        return 0.35 * math.exp(-(t % (4 * BEAT)) / 0.4)
    return math.exp(-((t - DROP) % BEAT) / 0.16)


def altitude(t):
    return sstep(11.0, 14.0, t) * (1 - sstep(17.0, 20.0, t))


def tilt(t):
    up = sstep(11.0, 12.2, t) - sstep(12.8, 14.0, t)
    down = sstep(17.0, 18.2, t) - sstep(18.8, 20.0, t)
    return math.radians(5.0) * (up - down)


def dawn(t):
    return sstep(0.8, 12.0, t)


def scene(t):
    pl = pulse(t)
    A = altitude(t)
    S = dawn(t)
    th = tilt(t)
    cx0, cy0 = ASP / 2, 0.5
    X = cx0 + (PX - cx0) * math.cos(th) - (PY - cy0) * math.sin(th)
    Y = cy0 + (PX - cx0) * math.sin(th) + (PY - cy0) * math.cos(th)
    H = HORIZON
    k = np.clip(Y / H, 0, 1)
    top = np.array([22, 20, 70], np.float32) * (1 - S) + np.array([80, 110, 190], np.float32) * S
    mid = np.array([130, 60, 140], np.float32) * (1 - S) + np.array([235, 150, 170], np.float32) * S
    low = np.array([150, 80, 100], np.float32) * (1 - S) + np.array([255, 195, 125], np.float32) * S
    img = mix(np.zeros_like(Y)[..., None] + top, mid, k ** 1.3)
    img = mix(img, low, np.clip((k - 0.6) / 0.4, 0, 1) ** 1.3)
    sy = H + 0.07 - 0.34 * sstep(2.0, 16.0, t)
    sd = np.hypot(X - 0.5, Y - sy)
    img = img + np.array([255, 140, 60], np.float32) * ((0.3 + 0.7 * S) * np.exp(-sd / 0.12))[..., None]
    img = mix(img, (255, 225, 150), np.clip((0.055 - sd) / 0.006, 0, 1))
    md = np.hypot(X - 1.08, Y - 0.17)
    moon = 1 - 0.65 * S
    img = mix(img, (235, 230, 210), np.clip((0.045 - md) / 0.006, 0, 1) * moon)
    img = img + np.array([120, 120, 150], np.float32) * (0.35 * moon * np.exp(-md / 0.08) * (md > 0.045))[..., None]
    xm = X + V_HILL * 0.6 * t
    ridge = periodic(xm, L_HILL, [(1, 0.05, 0.2), (3, 0.03, 1.1), (6, 0.015, 2.0)])
    peaks = 0.11 * np.abs(np.sin(2 * np.pi / L_HILL * 4 * xm + 0.7)) ** 3 + 0.06 * np.abs(np.sin(2 * np.pi / L_HILL * 7 * xm)) ** 4
    mount = H - 0.03 - ridge - peaks
    mcol = np.array([70, 60, 120], np.float32) * (1 - S) + np.array([150, 130, 190], np.float32) * S
    img = mix(img, mcol, np.clip((Y - mount) / 0.004, 0, 1) * 0.85)
    xh = X + V_HILL * t
    hill = H - 0.02 + 0.05 * A - periodic(xh, L_HILL, [(1, 0.03, 0.3), (2, 0.022, 1.7), (5, 0.01, 0.9), (9, 0.005, 2.2)])
    hc = np.array([60, 40, 85], np.float32) * (1 - S) + np.array([110, 85, 130], np.float32) * S
    img = mix(img, hc, np.clip((Y - hill) / 0.004, 0, 1))
    fy = H + 0.16 * A
    xt = X + V_TREE * t
    tops = periodic(xt, L_TREE, [(3, 0.014, 0.4), (7, 0.009, 1.1)]) + 0.02 * np.abs(np.sin(2 * np.pi / L_TREE * 37 * xt))
    tree = fy - 0.01 - tops
    tc = np.array([16, 10, 26], np.float32) * (1 - S) + np.array([40, 35, 55], np.float32) * S
    img = mix(img, tc, np.clip((Y - tree) / 0.004, 0, 1))
    mist = np.exp(-((Y - (H + 0.06)) / 0.05) ** 2) * A
    img = img + np.array([200, 170, 190], np.float32) * (0.35 * mist)[..., None]
    for vx, vh, vp in zip(VILL, VILL_H, VILL_P):
        cx = (vx - V_TREE * t) % L_TREE
        for rep in (cx - L_TREE, cx, cx + L_TREE):
            if -0.1 < rep < ASP + 0.1:
                d = np.hypot(X - rep, (Y - (fy - 0.005 - vh)) * 1.6)
                glow = (1.1 + 0.8 * pl * (0.5 + 0.5 * math.sin(vp))) * (1 - 0.6 * S) * np.exp(-d / 0.008)
                img = img + np.array([255, 190, 110], np.float32) * glow[..., None]
    gy = np.clip((Y - fy) / (1 - H), 0, 1)
    streak = 0.5 + 0.5 * periodic(X + V_GRND * t * (0.3 + gy), L_GRND, [(5, 0.6, 0.0), (11, 0.4, 1.0)])
    g0 = np.array([30, 22, 40], np.float32) * (1 - S) + np.array([55, 50, 60], np.float32) * S
    ground = mix(np.zeros_like(Y)[..., None] + g0, g0 * 0.45, gy)
    ground = ground * (0.8 + 0.4 * streak * gy)[..., None]
    img = np.where((Y > fy + 0.005)[..., None], ground, img)
    xg = X + V_GRASS * t
    grass = 0.9 + 0.4 * A - 0.035 * np.abs(np.sin(2 * np.pi / L_GRASS * 9 * xg)) - periodic(xg, L_GRASS, [(2, 0.02, 0.5), (5, 0.012, 1.3)])
    img = mix(img, (8, 6, 12), np.clip((Y - grass) / 0.006, 0, 1))
    xr = X + V_GRASS * 1.2 * t
    rocks = 1.12 - 0.3 * A - 0.06 * np.abs(np.sin(2 * np.pi / L_GRASS * 4 * xr)) ** 0.6 - periodic(xr, L_GRASS, [(3, 0.025, 0.2), (7, 0.012, 2.1)])
    img = mix(img, (12, 10, 16), np.clip((Y - rocks) / 0.006, 0, 1))
    off = (V_POLE * t) % POLE
    vis = 1 - sstep(0.15, 0.4, A)
    if vis > 0.01:
        for n in range(-1, 3):
            xp = n * POLE - off + 0.2
            img = mix(img, (10, 8, 14), ((np.abs(X - xp) < 0.012) & (Y > 0.12)) * vis)
            img = mix(img, (10, 8, 14), ((np.abs(X - xp) < 0.07) & (np.abs(Y - 0.17) < 0.006)) * vis)
            f = (X - xp) / POLE
            seg = (f >= 0) & (f <= 1)
            for y0 in (0.16, 0.19, 0.22):
                yw = y0 + 0.08 * (1 - (2 * f - 1) ** 2)
                img = mix(img, (8, 6, 12), (seg & (np.abs(Y - yw) < 0.006)) * vis)
    if T_TRAIN0 < t < T_TRAIN1:
        head = 1.5 - (t - T_TRAIN0) * 9.0
        tail = head + 12.5
        body = (X > head) & (X < tail) & (Y > 0.3) & (Y < 0.85)
        tw = (X + t * 9.0) % 0.3
        win = body & (np.abs(Y - 0.47) < 0.06) & (tw > 0.05) & (tw < 0.25)
        img = mix(img, (40, 44, 60), body)
        img = mix(img, (255, 215, 150), win)
        img = mix(img, (200, 60, 70), body & (np.abs(Y - 0.66) < 0.012))
        lamp = np.exp(-np.hypot(X - head, (Y - 0.62) * 1.5) / 0.03)
        img = img + np.array([255, 245, 220], np.float32) * (2.5 * lamp)[..., None]
    fr = 0.06
    rx = np.minimum(PX, ASP - PX)
    ry = np.minimum(PY, 1 - PY)
    corner = np.hypot(np.maximum(fr + 0.05 - rx, 0), np.maximum(fr + 0.05 - ry, 0)) > 0.05
    frame = (rx < fr) | (ry < fr) | corner
    edge = np.exp(-np.abs(np.minimum(rx, ry) - fr) / 0.006) * (~frame)
    img = img + np.array([255, 200, 150], np.float32) * (0.12 * edge)[..., None]
    img = mix(img, (34, 30, 38), frame)
    img = mix(img, (70, 60, 70), frame & (np.minimum(rx, ry) > fr - 0.01))
    small = img.reshape(ROWS, SS, COLS, SS, 3).mean((1, 3))
    for x, y, b, p in STARS:
        if y < fr + 0.01 or x < fr + 0.01 or x > ASP - fr - 0.01 or np.hypot(x - 1.08, y - 0.17) < 0.07:
            continue
        r, c = int(y * ROWS), int(x / ASP * COLS)
        tw = 0.55 * b * (0.6 + 0.4 * math.sin(t * 2.6 + p)) * (1 + 0.6 * pl) * (1 - S) ** 1.5
        small[r, c] = np.maximum(small[r, c], np.array([230, 230, 255], np.float32) * tw)
    return np.clip(small, 0, 255)


def glyphs(lum, t):
    pos = np.clip(lum * 0.85 + 0.12 + NOISE, 0, 0.999)
    idx = ORDER[(pos * len(ORDER)).astype(int)]
    flick = SHIM < 0.04 * (0.5 + 0.5 * math.sin(t * 7.0))
    rnd = ORDER[((SHIM * 997 + t * 13) % 1 * len(ORDER)).astype(int)]
    return np.where(flick, rnd, idx)


def gi(c):
    return CHARS.index(c) + 1


N_RAIN = 430
R_X = rng.uniform(-0.2, ASP + 0.5, N_RAIN)
R_P = rng.random(N_RAIN)
R_K = rng.integers(22, 40, N_RAIN)
R_B = rng.uniform(0.35, 1.0, N_RAIN)
RAIN_COL = np.array([170, 205, 255], np.float32)


def overlay(t, idx, col):
    fr = 0.065
    inside = lambda r, c: 0 <= r < ROWS and 0 <= c < COLS and fr < c / COLS * ASP < ASP - fr and fr < r / ROWS < 1 - fr
    pl = pulse(t)
    y = (R_P + R_K * t / DURATION) % 1.0 * 1.25 - 0.12
    x = R_X - 0.32 * y
    for xi, yi, b in zip(x, y, R_B):
        for j in range(5):
            yy, xx = yi - j * 0.02, xi + j * 0.0064
            r, c = int(yy * ROWS), int(xx / ASP * COLS)
            if inside(r, c):
                k = b * (1.15 - 0.2 * j) * (1 + 0.3 * pl)
                idx[r, c] = gi("/")
                col[r, c] = np.maximum(col[r, c], RAIN_COL * k)
    return idx, col


def state(t):
    col = scene(t)
    lum = col @ np.array([0.299, 0.587, 0.114], np.float32) / 255
    col = col * 1.6 / (1 + 0.6 * col / 255)
    return overlay(t, glyphs(lum, t), col)


def zoom_at(t):
    if t < T_ZOOM:
        e = sstep(0.15, T_ZOOM, t)
        return ZOOM0 ** (1 - e)
    if t > DURATION - 1.3:
        e = sstep(DURATION - 1.3, DURATION, t)
        return ZOOM0 ** e
    return 1.0


def compose(idx, col, z=1.0):
    zi = max(1, int(math.ceil(z - 1e-6)))
    at, cw, ch = atlas(FONT * zi) if zi > 1 else (AT, CW, CH)
    vc = min(COLS, int(math.ceil(COLS / z)) + 2)
    vr = min(ROWS, int(math.ceil(ROWS / z)) + 2)
    c0, r0 = (COLS - vc) // 2, (ROWS - vr) // 2
    idx, col = idx[r0:r0 + vr, c0:c0 + vc], col[r0:r0 + vr, c0:c0 + vc]
    g = at[idx]
    base = BG + 0 * col[..., :1]
    img = base[:, :, None, None, :] + g[..., None] * (col[:, :, None, None, :] - base[:, :, None, None, :])
    img = img.transpose(0, 2, 1, 3, 4).reshape(vr * ch, vc * cw, 3)
    img8 = np.clip(img, 0, 255).astype(np.uint8)
    glow = np.asarray(Image.fromarray(img8).filter(ImageFilter.GaussianBlur(4 * zi)), np.float32)
    out = Image.fromarray(np.clip(img + 0.35 * glow, 0, 255).astype(np.uint8))
    if zi == 1 and z <= 1.0001:
        frame = Image.new("RGB", (IMG_W, IMG_H), tuple(int(v) for v in BG))
        frame.paste(out, ((IMG_W - out.width) // 2, (IMG_H - out.height) // 2))
        return frame
    s = z / zi
    cx, cy = out.width / 2, out.height / 2
    w = IMG_W / s
    h = IMG_H / s
    crop = out.crop((int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2)))
    return crop.resize((IMG_W, IMG_H), Image.BILINEAR)


def render(t):
    idx, col = state(t)
    return compose(idx, col, zoom_at(t))


KW = {"def", "return", "import", "from", "for", "in", "if", "else", "elif", "while", "class",
      "and", "or", "not", "None", "True", "False", "lambda", "with", "as"}
TOKEN = re.compile(r'("[^"]*"|\'[^\']*\')|(\b\d+\.?\d*\b)|([A-Za-z_]\w*)|(.)')
C_TXT, C_KW, C_STR, C_NUM, C_FN = (169, 183, 198), (204, 120, 50), (106, 135, 89), (104, 151, 187), (255, 198, 109)
WIN_W = 1040
WIN_H = int(WIN_W * IMG_H / IMG_W)
WIN_Y = 520
_ide = {}


def ide_layers():
    if _ide:
        return _ide
    lines = open(__file__, encoding="utf8").read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("def scene("))
    lines = lines[start - 30:start + 60]
    f = load_font("mono", 21)
    fb = load_font("mono_b", 21)
    lh, gut = 27, 66
    code = Image.new("RGB", (VW, lh * len(lines) + 40), (43, 43, 43))
    d = ImageDraw.Draw(code)
    d.rectangle((0, 0, gut - 8, code.height), fill=(49, 51, 53))
    for i, line in enumerate(lines):
        y = 10 + i * lh
        d.text((gut - 14, y), str(start - 29 + i), font=f, fill=(96, 99, 102), anchor="ra")
        x, prev = gut + 6, ""
        for m in TOKEN.finditer(line):
            tok = m.group(0)
            ft = f
            if m.group(1):
                c = C_STR
            elif m.group(2):
                c = C_NUM
            elif m.group(3) and tok in KW:
                c, ft = C_KW, fb
            elif m.group(3) and prev == "def":
                c = C_FN
            else:
                c = C_TXT
            d.text((x, y), tok, font=ft, fill=c)
            x += f.getlength(tok)
            if m.group(3):
                prev = tok
            if x > VW:
                break
    top = Image.new("RGB", (VW, 64), (60, 63, 65))
    dt = ImageDraw.Draw(top)
    dt.rectangle((0, 0, 210, 64), fill=(43, 43, 43))
    dt.rectangle((0, 60, 210, 64), fill=(74, 136, 199))
    dt.text((24, 18), "train.py", font=load_font("ui", 24), fill=(200, 200, 200))
    run = Image.new("RGB", (VW, 250), (43, 43, 43))
    dr = ImageDraw.Draw(run)
    dr.rectangle((0, 0, VW, 46), fill=(60, 63, 65))
    dr.text((20, 9), "Run:   train", font=load_font("ui", 22), fill=(200, 200, 200))
    dr.text((20, 66), "> python train.py", font=f, fill=C_TXT)
    dr.text((20, 100), f"{COLS}x{ROWS} chars  |  {len(CHARS)} glyphs  |  80 bpm", font=f, fill=C_STR)
    title = Image.new("RGB", (WIN_W, 36), (243, 243, 243))
    dti = ImageDraw.Draw(title)
    dti.text((40, 7), "night train", font=load_font("ui", 18), fill=(20, 20, 20))
    dti.ellipse((12, 10, 28, 26), outline=(70, 120, 200), width=3)
    sym = load_font("sym", 18)
    for i, ch_ in enumerate(("—", "☐", "✕")):
        dti.text((WIN_W - 140 + i * 46, 6), ch_, font=sym, fill=(30, 30, 30))
    shadow = Image.new("L", (WIN_W + 80, 36 + WIN_H + 80), 0)
    ImageDraw.Draw(shadow).rectangle((40, 40, 40 + WIN_W, 40 + 36 + WIN_H), fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    _ide.update(code=code, top=top, run=run, title=title, shadow=shadow)
    return _ide


def to_ide(frame, t):
    e = ide_layers()
    out = Image.new("RGB", (VW, VH), (43, 43, 43))
    scroll = int(300 * (1 - math.cos(2 * math.pi * t / DURATION)) / 2)
    out.paste(e["code"].crop((0, scroll, VW, scroll + VH - 64 - 250)), (0, 64))
    out.paste(e["top"], (0, 0))
    out.paste(e["run"], (0, VH - 250))
    out.paste(Image.new("RGB", e["shadow"].size, (0, 0, 0)), (20 - 40, WIN_Y - 40 + 6), e["shadow"])
    out.paste(e["title"], (20, WIN_Y))
    out.paste(frame.resize((WIN_W, WIN_H), Image.LANCZOS), (20, WIN_Y + 36))
    return np.asarray(out)


def export(path, audio=None, ide=True):
    w, h = (VW, VH) if ide else (IMG_W, IMG_H)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-ss", f"{AUDIO_START:.3f}", "-t", str(DURATION), "-i", audio, "-map", "0:v", "-map", "1:a",
                "-af", f"afade=t=in:d=0.05,afade=t=out:st={DURATION - 0.6:.2f}:d=0.6", "-c:a", "aac", "-b:a", "320k"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
            "-t", str(DURATION), "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        t = i / FPS
        fr = render(t)
        p.stdin.write((to_ide(fr, t) if ide else np.asarray(fr)).tobytes())
        if i % 120 == 0:
            print(f"{i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("done:", path)


def live(width=840):
    import time
    import tkinter as tk
    from PIL import ImageTk
    root = tk.Tk()
    root.title("night train")
    root.configure(bg="black")
    view = tk.Label(root, bg="black", bd=0)
    view.pack()
    size = (width, int(width * IMG_H / IMG_W))
    t0 = time.perf_counter()

    def step():
        t = (time.perf_counter() - t0) % DURATION
        view.photo = ImageTk.PhotoImage(render(t).resize(size, Image.BILINEAR))
        view.configure(image=view.photo)
        root.after(1, step)

    step()
    root.mainloop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--export")
    ap.add_argument("--audio")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--out", default="stills")
    ap.add_argument("--plain", action="store_true")
    a = ap.parse_args()
    if a.still:
        os.makedirs(a.out, exist_ok=True)
        for s in a.still:
            fr = render(s)
            (fr if a.plain else Image.fromarray(to_ide(fr, s))).save(f"{a.out}/t{s:05.2f}.png")
        print("stills ok", COLS, "x", ROWS)
    elif a.export:
        export(a.export, a.audio, ide=not a.plain)
    else:
        live()

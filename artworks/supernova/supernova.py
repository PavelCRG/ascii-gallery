import argparse
import math
import os
import re
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FPS = 60
DURATION = 24.0
VW, VH = 1080, 1920
BG = np.array([12, 12, 16], np.float32)
FONT = 10

BPM = 87.5
BEATP = 60.0 / BPM
AUDIO_START = 43.97

T_PRINT = 0.9
T_GIANT0, T_GIANT1 = 6.0, 10.0
T_COL0, T_BANG = 10.3, 10.9
T_PULSAR = 12.3
T_BACK0, T_BACK1 = 19.0, 23.0
T_END = 23.8

CHARS = "".join(chr(c) for c in range(32, 127))
I_DOT, I_STAR = CHARS.index("."), CHARS.index("*")
I_DASH, I_SLASH, I_BAR, I_BSLASH = (CHARS.index(c) for c in "-/|\\")

NEB = np.array([[60, 230, 230], [255, 60, 190], [255, 200, 60], [165, 90, 255], [70, 160, 255], [255, 90, 60]], np.float32)
WHITE = np.array([255, 245, 230], np.float32)


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
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def pulse(t):
    return math.exp(-((t - T_BANG) % BEATP) / 0.12)


def char_for(dx, dy):
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return np.select([ang < 22, ang < 68, ang < 112, ang < 158], [I_DASH, I_SLASH, I_BAR, I_BSLASH], I_DASH)


def atlas(size):
    font = load_font("mono_b", size)
    cw = int(round(font.getlength("M")))
    asc, desc = font.getmetrics()
    ch = asc + desc - 1
    at = np.zeros((len(CHARS), ch, cw), np.float32)
    for i, c in enumerate(CHARS):
        im = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
        at[i] = np.clip(np.asarray(im, np.float32) / 255 * 1.25, 0, 1) ** 0.75
    return at, cw, ch


AT, CW, CH = atlas(FONT)
COLS, ROWS = VW // CW, VH // CH
X0, Y0 = (VW - COLS * CW) // 2, (VH - ROWS * CH) // 2
U0 = VH / 2


def source_chars():
    text = open(__file__, encoding="utf8").read()
    return np.array([CHARS.index(c) if c in CHARS else I_DOT for c in re.sub(r"\s+", " ", text)])


SRC = source_chars()
GX = (np.arange(COLS) * CW + X0 + CW / 2 - VW / 2) / U0
GY = (VH / 2 - (np.arange(ROWS) * CH + Y0 + CH / 2)) / U0
GX, GY = np.meshgrid(GX, GY)
RR = np.hypot(GX, GY) + 1e-5
ANG = np.arctan2(GY, GX)
CELL = np.arange(ROWS)[:, None] * COLS + np.arange(COLS)[None, :]
CODE = SRC[CELL % len(SRC)]

rng = np.random.default_rng(7)
ST_B = np.where(rng.random((ROWS, COLS)) < 0.012, 0.15 + 0.55 * rng.random((ROWS, COLS)) ** 2, 0.0).astype(np.float32)
ST_M = rng.integers(1, 12, (ROWS, COLS))
ST_PH = rng.uniform(0, 2 * np.pi, (ROWS, COLS))
NW = 16
W_DIR = rng.uniform(0, 2 * np.pi, NW)
W_K = rng.uniform(6, 22, NW)
W_M = rng.integers(2, 9, NW) * rng.choice([-1, 1], NW)
W_PH = rng.uniform(0, 2 * np.pi, NW)
A_K = rng.integers(3, 17, NW)
A_M = rng.integers(1, 6, NW) * rng.choice([-1, 1], NW)
A_PH = rng.uniform(0, 2 * np.pi, NW)


def turb(x, y, t, scale=1.0):
    w = 2 * np.pi * t / DURATION
    n = np.zeros_like(x)
    for i in range(NW):
        n += np.sin(scale * W_K[i] * (x * math.cos(W_DIR[i]) + y * math.sin(W_DIR[i])) + W_M[i] * w + W_PH[i])
    return n / math.sqrt(NW / 2)


def aturb(a, t, extra=0.0):
    w = 2 * np.pi * t / DURATION
    n = np.zeros_like(a)
    for i in range(NW):
        n += np.sin(A_K[i] * a + A_M[i] * w + A_PH[i] + extra * (i % 3)) / (1 + 0.15 * A_K[i])
    return n / 1.6


def star_radius(t):
    grow = 0.16 + 0.04 * float(sstep(0.0, T_GIANT0, t)) + 0.11 * float(sstep(T_GIANT0, T_GIANT1, t))
    wob = 0.018 * float(sstep(T_GIANT0 + 1.5, T_COL0, t)) * math.sin((t - T_BANG) * 2 * math.pi / BEATP)
    col = 1 - float(sstep(T_COL0, T_BANG, t)) ** 2.2
    return (grow + wob) * col


def shell_radius(t):
    if t < T_BANG:
        return 0.0
    out = 0.66 * (1 - math.exp(-(t - T_BANG) / 0.9))
    back = float(sstep(T_BACK0, T_BACK1, t))
    return out * (1 - back) + 0.02 * back


def render(t, rows=None):
    pl = pulse(t)
    col = np.zeros((ROWS, COLS, 3), np.float32)
    idx = CODE.copy()
    tw = 0.6 + 0.4 * np.sin(2 * np.pi * (t / DURATION) * ST_M + ST_PH)
    col += np.array([200, 210, 255], np.float32) * (ST_B * tw)[..., None]
    idx = np.where(ST_B > 0, np.where(ST_B > 0.5, I_STAR, I_DOT), idx)
    red = float(sstep(1.0, T_GIANT1, t))
    R = star_radius(t)
    alive = t < T_BANG
    if alive and R > 0.003:
        q = RR / R
        n = turb(GX / max(R, 0.05) * 0.22, GY / max(R, 0.05) * 0.22, t)
        gran = 0.5 + 0.5 * np.tanh(n)
        inside = q < 1
        limb = np.sqrt(np.clip(1 - q ** 2, 0, 1))
        hot = np.array([255, 238, 175], np.float32)
        warm = np.array([255, 190, 70], np.float32) * (1 - red) + np.array([255, 85, 40], np.float32) * red
        edge = np.array([255, 120, 40], np.float32) * (1 - red) + np.array([200, 30, 30], np.float32) * red
        c = np.where((limb > 0.6)[..., None], hot + (warm - hot) * ((1 - limb) / 0.4)[..., None],
                     warm + (edge - warm) * ((0.6 - limb) / 0.6)[..., None])
        c = c * (1 - 0.35 * red * (limb > 0.6))[..., None]
        b = (0.5 + 0.75 * gran ** 1.6) * (0.4 + 0.75 * limb) * (1 + 0.3 * pl)
        unstable = float(sstep(T_GIANT0 + 1.5, T_COL0, t))
        b = b * (1 + unstable * 0.5 * np.maximum(0, n) * pl)
        col += np.where(inside[..., None], c * b[..., None], 0)
        idx = np.where(inside, SRC[(CELL + (gran * 7).astype(np.int64) * 131) % len(SRC)], idx)
        fl = aturb(ANG + 2.5 * np.maximum(RR - R, 0), t)
        reach = R * (0.07 + 0.16 * np.maximum(0, fl) ** 2 + 0.05 * pl)
        cor = np.exp(-np.maximum(q - 1, 0) * R / np.maximum(reach, 1e-3)) * (~inside)
        cor = cor * (0.4 + 0.6 * np.maximum(0, fl))
        col += (edge * 1.1)[None, None, :] * cor[..., None]
        if t > T_COL0:
            k = float(sstep(T_COL0, T_BANG, t))
            rays = np.maximum(0, aturb(ANG * 3, t, 1.0)) ** 3
            infall = rays * np.exp(-((RR - (1 - k) * 0.45) / 0.15) ** 2) * k * 2.0
            m = (infall > 0.15) & ~inside
            col += WHITE[None, None, :] * 0.8 * infall[..., None] * m[..., None]
            idx = np.where(m, char_for(GX * CH, GY * CW), idx)
    S = shell_radius(t)
    if t >= T_BANG and S > 0.005:
        age = t - T_BANG
        back = float(sstep(T_BACK0, T_BACK1, t))
        q = RR / S
        rot = 0.25 * age
        a = ANG + rot * 0.15
        fil = 1 - np.abs(np.tanh(turb(np.cos(a) * 2.2 + q * 0.7, np.sin(a) * 2.2 - q * 0.5, t * 0.5, 0.9)))
        fil = fil ** 5
        shell = np.exp(-((q - 0.8) / 0.22) ** 2) + 0.25 * np.exp(-(q / 0.4) ** 2)
        dens = shell * (0.12 + 2.0 * fil) * (q < 1.08)
        hue = ((a / (2 * np.pi)) % 1.0) * len(NEB) + q * 1.5
        h0 = np.floor(hue).astype(np.int64)
        hf = (hue - h0)[..., None]
        nc = NEB[h0 % len(NEB)] + (NEB[(h0 + 1) % len(NEB)] - NEB[h0 % len(NEB)]) * hf
        heat = np.clip(1 - age / 1.6, 0, 1) + back * 0.7
        nc = nc + (WHITE - nc) * np.clip(heat * (1 - q * 0.5), 0, 1)[..., None]
        fade = 1.0 - float(sstep(T_BACK1 - 0.6, T_END, t))
        nb = dens * (1.0 + 0.3 * pl) * fade * (1 + 0.8 * back)
        col += nc * nb[..., None]
        for off, cc, amp in ((0.0, (255, 245, 235), 1.6), (-0.08, (255, 70, 110), 1.0), (-0.16, (70, 150, 255), 0.9)):
            ring = np.exp(-((q - 1.0 - off) / 0.03) ** 2) * amp * math.exp(-age * 0.45) * (1 - back)
            m = ring > 0.12
            col[m] = np.maximum(col[m], np.array(cc, np.float32) * ring[m][:, None])
            idx = np.where(m, I_DOT, idx)
        idx = np.where(dens > 0.05, SRC[(CELL * 7 + (fil * 5).astype(np.int64) * 977) % len(SRC)], idx)
        pk = float(sstep(T_PULSAR, T_PULSAR + 1.0, t)) * (1 - float(sstep(T_BACK0, T_BACK0 + 1.5, t)))
        if pk > 0:
            th = 2 * np.pi * (t - T_PULSAR) / 3.0
            d1 = np.abs(((ANG - th) + np.pi) % (2 * np.pi) - np.pi)
            d2 = np.abs(((ANG - th - np.pi) + np.pi) % (2 * np.pi) - np.pi)
            beam = (np.exp(-(np.minimum(d1, d2) * RR / 0.012) ** 2) * np.exp(-RR / 0.7)) * pk * 1.8
            m = beam > 0.12
            bc = np.array([150, 220, 255], np.float32)
            col += bc * beam[..., None]
            idx = np.where(m, char_for(GX * CH, GY * CW), idx)
    core_r = 0.015 + 0.012 * pl
    if t >= T_BANG:
        core_k = 1.2 * (1 - float(sstep(T_BACK1 - 0.5, T_END, t))) + 0.8 * float(sstep(T_BACK0, T_BACK1, t))
    else:
        core_k = float(sstep(T_COL0 + 0.2, T_BANG, t)) * 1.5
    core = np.exp(-RR / core_r) * core_k
    col += WHITE * core[..., None]
    idx = np.where(core > 0.4, I_STAR, idx)
    if T_BANG - 0.1 < t < T_BANG + 0.6:
        if t < T_BANG:
            k = float(sstep(T_BANG - 0.1, T_BANG, t))
            col += WHITE * (2.5 * k * np.exp(-RR / 0.04))[..., None]
        else:
            age = t - T_BANG
            hit = math.exp(-age / 0.06)
            col += WHITE * (2.4 * hit * np.exp(-RR / 0.55) + 1.2 * math.exp(-age / 0.25) * np.exp(-RR / 0.08))[..., None]
            idx = np.where((hit * np.exp(-RR / 0.55) > 0.35) & (idx == 0), I_STAR, idx)
    if t < T_PRINT:
        rows = np.arange(ROWS)[:, None] * np.ones((1, COLS))
        top, bot = 39, 153
        front = top + (bot - top + 8) * t / T_PRINT
        shown = rows < front
        cur = np.exp(-((rows - front) / 1.2) ** 2)
        col = col * shown[..., None]
        col += np.array([200, 220, 255], np.float32) * (cur * 0.8)[..., None] * (CODE != 0)[..., None]
        idx = np.where(cur > 0.3, CODE, idx)
    col = np.minimum(col, 340)
    r0, r1 = rows if rows else (0, ROWS)
    col, idx = col[r0:r1], idx[r0:r1]
    has = (col.max(-1) > 14) & (idx != 0)
    g = AT[idx] * has[:, :, None, None]
    hitk = math.exp(-(t - T_BANG) / 0.07) if t >= T_BANG else 0.0
    base = BG + (0.03 + 0.7 * hitk) * col
    img = base[:, :, None, None, :] + g[..., None] * (col[:, :, None, None, :] - base[:, :, None, None, :])
    img = img.transpose(0, 2, 1, 3, 4).reshape((r1 - r0) * CH, COLS * CW, 3)
    img8 = np.clip(img, 0, 255).astype(np.uint8)
    glow = np.asarray(Image.fromarray(img8).filter(ImageFilter.GaussianBlur(5)), np.float32)
    out = np.clip(img + 0.6 * glow, 0, 255).astype(np.uint8)
    if rows:
        if T_BANG <= t < T_BANG + 0.7:
            a = 18 * math.exp(-(t - T_BANG) / 0.18)
            out = np.roll(out, (int(a * math.sin(t * 91)), int(a * math.cos(t * 73))), (0, 1))
        return out
    canvas = np.zeros((VH, VW, 3), np.uint8)
    canvas[:] = BG.astype(np.uint8)
    canvas[Y0:Y0 + out.shape[0], X0:X0 + out.shape[1]] = out
    if T_BANG <= t < T_BANG + 0.7:
        a = 18 * math.exp(-(t - T_BANG) / 0.18)
        canvas = np.roll(canvas, (int(a * math.sin(t * 91)), int(a * math.cos(t * 73))), (0, 1))
    return canvas


KW = {"def", "return", "import", "from", "for", "in", "if", "else", "elif", "while", "class",
      "and", "or", "not", "None", "True", "False", "lambda", "with", "as"}
TOKEN = re.compile(r'("[^"]*"|\'[^\']*\')|(\b\d+\.?\d*\b)|([A-Za-z_]\w*)|(.)')
C_TXT, C_KW, C_STR, C_NUM, C_FN = (169, 183, 198), (204, 120, 50), (106, 135, 89), (104, 151, 187), (255, 198, 109)
WIN_W, WIN_H = 1040, 1100
WIN_Y = 470
_ide = {}


def ide_layers():
    if _ide:
        return _ide
    lines = open(__file__, encoding="utf8").read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("def render("))
    lines = lines[start - 20:start + 70]
    f = load_font("mono", 21)
    fb = load_font("mono_b", 21)
    seg = load_font("ui", 22)
    lh, gut = 27, 66
    code = Image.new("RGB", (VW, lh * len(lines) + 40), (43, 43, 43))
    d = ImageDraw.Draw(code)
    d.rectangle((0, 0, gut - 8, code.height), fill=(49, 51, 53))
    for i, line in enumerate(lines):
        y = 10 + i * lh
        d.text((gut - 14, y), str(start - 19 + i), font=f, fill=(96, 99, 102), anchor="ra")
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
    dt.rectangle((0, 0, 260, 64), fill=(43, 43, 43))
    dt.rectangle((0, 60, 260, 64), fill=(74, 136, 199))
    dt.text((24, 18), "supernova.py", font=load_font("ui", 24), fill=(200, 200, 200))
    run = Image.new("RGB", (VW, 250), (43, 43, 43))
    dr = ImageDraw.Draw(run)
    dr.rectangle((0, 0, VW, 46), fill=(60, 63, 65))
    dr.text((20, 9), "Run:   supernova", font=seg, fill=(200, 200, 200))
    dr.text((20, 66), "> python supernova.py", font=f, fill=C_TXT)
    dr.text((20, 100), f"{COLS}x{ROWS} chars  |  {len(SRC)} glyphs of its own code  |  30 fps", font=f, fill=C_STR)
    title = Image.new("RGB", (WIN_W, 36), (243, 243, 243))
    dti = ImageDraw.Draw(title)
    dti.text((40, 7), "supernova", font=load_font("ui", 18), fill=(20, 20, 20))
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
    s = WIN_W / VW
    ch_ = int(WIN_H / s)
    y0 = (VH - ch_) // 2
    win = Image.fromarray(frame[y0:y0 + ch_]).resize((WIN_W, WIN_H), Image.LANCZOS)
    out.paste(win, (20, WIN_Y + 36))
    return np.asarray(out)


def export(path, audio=None, ide=True):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-ss", f"{AUDIO_START:.3f}", "-t", str(DURATION), "-i", audio, "-map", "0:v", "-map", "1:a",
                "-af", f"afade=t=in:d=0.05,afade=t=out:st={DURATION - 0.6:.2f}:d=0.6", "-c:a", "aac", "-b:a", "320k"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-t", str(DURATION), "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        fr = render(i / FPS)
        if ide:
            fr = to_ide(fr, i / FPS)
        p.stdin.write(fr.tobytes())
        if i % 60 == 0:
            print(f"{i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("done:", path)


def live(width=720):
    import tkinter as tk
    from PIL import ImageTk
    root = tk.Tk()
    root.title("supernova")
    root.configure(bg="black")
    view = tk.Label(root, bg="black", bd=0)
    view.pack()
    h = int(WIN_H / (WIN_W / VW))
    r0 = max(0, ((VH - h) // 2 - Y0) // CH)
    r1 = min(ROWS, r0 + h // CH + 1)
    size = (width, int(width * (r1 - r0) * CH / (COLS * CW)))
    t0 = time.perf_counter()

    def step():
        t = (time.perf_counter() - t0) % DURATION
        img = Image.fromarray(render(t, (r0, r1))).resize(size, Image.BILINEAR)
        view.photo = ImageTk.PhotoImage(img)
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
            Image.fromarray(fr if a.plain else to_ide(fr, s)).save(f"{a.out}/t{s:05.2f}.png")
        print("stills ok", COLS, "x", ROWS)
    elif a.export:
        export(a.export, a.audio, ide=not a.plain)
    else:
        live()

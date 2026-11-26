"""Чёрная дыра засасывает код этой же программы. Всё в 3D: стена кода, огненный диск,
галактика после взрыва; камера отъезжает от крупного кода, поднимается над диском,
облетает его сбоку, трясётся на ударе. Петля: конец и начало — пустое небо.

Кадры:   python blackhole.py --still 0.5 1.5 3 8 14 16.95 17.6 18.5
Видео:   python blackhole.py --export blackhole.mp4 --audio music/silver_tears_slowed.m4a
"""
import argparse
import io
import math
import os
import re
import subprocess
import tokenize

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FPS = 30
DURATION = 30.0
VW, VH = 1080, 1920
BG = np.array([14, 14, 18], np.float32)

T_HOLE = 2.1       # появляется дыра (на долю трека)
T_TENSE = 12.6     # нагнетание перед ударом
T_COLLAPSE = 16.6  # дыра схлопывается
T_FLASH = 16.9     # вспышка на ударе трека
T_BACK = 29.4      # камера возвращается в начало петли

# трек silver tears (Slowed): удар после затишья на 43.07 с совпадает со вспышкой
AUDIO_START = 43.07 - T_FLASH
BEATP, BEATO = 0.672, 0.084  # доли трека (89 BPM) внутри используемого куска

CHARS = "".join(chr(c) for c in range(32, 127))
I_DOT, I_STAR = CHARS.index("."), CHARS.index("*")
I_DASH, I_SLASH, I_BAR, I_BSLASH = (CHARS.index(c) for c in "-/|\\")


T_RE = BEATO + 30 * BEATP   # на долю: в центре рождается новая дыра и тянет галактику обратно
T_EAT = 27.9                 # к этому моменту съедено всё
T_GONE0, T_GONE1 = 28.3, 28.9  # новая дыра тихо исчезает


def pulse(t):
    ph = (t - BEATO) % BEATP
    return math.exp(-ph / 0.09)


def sstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, k):
    return a + (b - a) * k


def char_for(dx, dy):
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return np.select([ang < 22, ang < 68, ang < 112, ang < 158], [I_DASH, I_SLASH, I_BAR, I_BSLASH], I_DASH)


_atlas = {}


def atlas(size):
    if size not in _atlas:
        font = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", size)
        cw = int(round(font.getlength("M")))
        asc, desc = font.getmetrics()
        ch = asc + desc + 1
        at = np.zeros((len(CHARS), ch, cw), np.float32)
        for i, c in enumerate(CHARS):
            im = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
            at[i] = np.clip(np.asarray(im, np.float32) / 255 * 1.25, 0, 1) ** 0.75
        _atlas[size] = (at, cw, ch)
    return _atlas[size]


_, CW0, CH0 = atlas(9)
COLS0, ROWS0 = VW // CW0, VH // CH0
U0 = VH / 2  # пикселей на единицу экрана


def clean_source():
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


KW = {"def", "return", "import", "from", "for", "in", "if", "else", "elif", "while", "class",
      "and", "or", "not", "None", "True", "False", "lambda", "with", "as"}
TOKEN = re.compile(r'("[^"]*"|\'[^\']*\')|(\b\d+\.?\d*\b)|([A-Za-z_]\w*)|(.)')
C_TXT, C_KW, C_STR, C_NUM, C_FN = (169, 183, 198), (204, 120, 50), (106, 135, 89), (104, 151, 187), (255, 198, 109)


def code_wall():
    stream = []
    for line in clean_source():
        prev = ""
        for m in TOKEN.finditer(line.strip()):
            tok = m.group(0)
            if m.group(1):
                colr = C_STR
            elif m.group(2):
                colr = C_NUM
            elif m.group(3) and tok in KW:
                colr = C_KW
            elif m.group(3) and prev == "def":
                colr = C_FN
            else:
                colr = C_TXT
            stream += [(c, colr) for c in tok]
            if m.group(3):
                prev = tok
        stream += [(" ", C_TXT), (" ", C_TXT)]
    cells, i = [], 0
    for row in range(ROWS0):
        for x in range(COLS0):
            c, colr = stream[i % len(stream)]
            i += 1
            if c != " " and c in CHARS:
                cells.append((row, x, c, colr))
    return cells


WALL = code_wall()
P_CH = np.array([CHARS.index(c[2]) for c in WALL])
P_RGB = np.array([c[3] for c in WALL], np.float32)
NP = len(WALL)
CY0 = 0.06
# мир: дыра в начале координат, стена кода в плоскости z=0, камера смотрит с +z
WX = (np.array([c[1] for c in WALL]) + 0.5 - COLS0 / 2) * CW0 / U0
WY = -(np.array([c[0] for c in WALL]) + 0.5 - ROWS0 / 2) * CH0 / U0 - CY0
R0 = np.hypot(WX, WY)
TH0 = np.arctan2(WY, WX)
RMAX = R0.max()

rng = np.random.default_rng(5)
TAU = 2.4 + 5.4 * (R0 / RMAX) ** 1.3 + rng.uniform(0, 0.5, NP)
DUR = 2.5 + 5.0 * (R0 / RMAX) + rng.uniform(-0.3, 0.3, NP)
# часть букв кружит дольше всех и падает в дыру прямо перед ударом
LATE = rng.random(NP) < 0.09
TAU[LATE] = 7.5 + 2.5 * rng.random(LATE.sum())
DUR[LATE] = (16.3 - TAU[LATE]) * (0.75 + 0.25 * rng.random(LATE.sum()))

FLY_T = 1.0
FLY_S = rng.uniform(0.0, 0.6, NP)
FLY_A = rng.uniform(0, 2 * np.pi, NP)
FLY_Z = 1.6 + 1.4 * rng.random(NP)   # прилетают из-за камеры

EX_S = T_FLASH + 0.3 * rng.random(NP)
EX_V = 0.3 + 1.5 * rng.random(NP) ** 1.3
ARMS = 5
EX_A = rng.integers(0, ARMS, NP) * (2 * np.pi / ARMS) + rng.normal(0, 0.10, NP)
_free = rng.random(NP) < 0.10
EX_A[_free] = rng.uniform(0, 2 * np.pi, _free.sum())
EX_ARM = np.round(EX_A / (2 * np.pi / ARMS)).astype(int) % ARMS
# свой цвет у каждого рукава: бирюзовый, малиновый, золотой, фиолетовый, голубой
ARM_COL = np.array([[60, 230, 230], [255, 60, 190], [255, 200, 60], [165, 90, 255], [70, 160, 255]], np.float32)
EX_TW = rng.random(NP) < 0.08          # блёстки
EX_TWP = rng.random(NP) * 6.28
RAYS = 28
RAY_A = rng.uniform(0, 2 * np.pi, RAYS)
RAY_L = 0.6 + 0.9 * rng.random(RAYS)
EX_H = rng.normal(0, 0.03, NP)
BETA = math.radians(38)  # наклон плоскости галактики к камере
E1 = np.array([1.0, 0.0, 0.0])
E2 = np.array([0.0, math.sin(BETA), -math.cos(BETA)])
EN = np.array([0.0, math.cos(BETA), math.sin(BETA)])

NSTAR = 900
ST = np.stack([rng.uniform(-7, 7, NSTAR), rng.uniform(-7, 7, NSTAR), np.full(NSTAR, -5.0)], 1)
ST_B = 0.25 + 0.6 * rng.random(NSTAR) ** 2
ST_PH = rng.random(NSTAR) * 6.28


def temp_color(r):
    k = np.clip((0.75 - r) / 0.65, 0, 1)[:, None]
    far = np.array([170, 40, 150], np.float32)
    mid = np.array([255, 110, 30], np.float32)
    near = np.array([255, 235, 180], np.float32)
    return np.where(k < 0.5, far + (mid - far) * (k * 2), mid + (near - mid) * (k * 2 - 1))


# ---------- камера ----------
D0 = 4.0
F = D0


def zoom(t):
    if t < 1.0:
        return 3.0
    if t < 2.6:
        return lerp(3.0, 1.0, float(sstep(1.0, 2.6, t)))
    if t < T_TENSE:
        return lerp(1.0, 1.25, float(sstep(2.6, T_TENSE, t)))
    if t < T_FLASH:
        return lerp(1.25, 1.6, float(sstep(T_TENSE, T_COLLAPSE, t)))
    if t < T_BACK:
        z = lerp(1.6, 0.85, 1 - (1 - min(1.0, (t - T_FLASH) / 0.6)) ** 3)
        z -= 0.05 * float(sstep(T_FLASH + 0.6, T_RE, t))
        return z + 0.55 * float(sstep(T_RE, T_GONE1, t))  # наезд вслед за галактикой
    return lerp(0.8, 3.0, float(sstep(T_BACK, DURATION, t)))


def elev(t):
    e = 22 * float(sstep(2.4, 6.5, t)) + 3 * math.sin(t * 0.7) * float(sstep(4, 7, t))
    e += 8 * float(sstep(T_FLASH, T_BACK, t))
    return math.radians(e * (1 - float(sstep(T_BACK, DURATION, t))))


def azim(t):
    a = 24 * float(sstep(2.4, T_COLLAPSE, t)) + 16 * float(sstep(T_COLLAPSE, T_RE, t)) + 14 * float(sstep(T_RE, T_BACK, t))
    return math.radians(a * (1 - float(sstep(T_BACK, DURATION, t))))


def shake(t):
    amp = 0.006 * float(sstep(T_TENSE, T_COLLAPSE, t))
    if t >= T_FLASH:
        amp += 0.05 * math.exp(-(t - T_FLASH) * 4)
    return amp * np.array([math.sin(t * 71) + 0.5 * math.sin(t * 113), math.sin(t * 83 + 1) + 0.5 * math.sin(t * 131), 0])


def camera(t):
    D = D0 / zoom(t)
    el, az = elev(t), azim(t)
    T = shake(t)
    C = T + D * np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
    f = (T - C) / np.linalg.norm(T - C)
    r = np.cross(f, [0, 1, 0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return C, r, u, f


def project(P, cam):
    C, r, u, f = cam
    d = P - C
    z = d @ f
    zz = np.maximum(z, 1e-3)
    return F * (d @ r) / zz, F * (d @ u) / zz, z


# ---------- симуляция падения ----------
class Sim:
    def __init__(self):
        self.t = 0.0
        self.r = R0.copy()
        self.th = TH0.copy()
        self.alive = np.ones(NP, bool)
        self.k = (R0 ** 2 - 0.0036) / DUR
        self.eaten_now = 0.0

    def rh(self, t):
        frac = 1 - self.alive.mean()
        base = 0.055 * float(sstep(T_HOLE, T_HOLE + 1.0, t)) + 0.075 * frac
        return base * (1 - float(sstep(T_COLLAPSE, T_COLLAPSE + 0.3, t)))

    def step(self, dt):
        t = self.t
        rel = (t >= TAU) & self.alive & (t < T_COLLAPSE)
        spin_in = sstep(TAU, TAU + 1.0, t)
        dr = -self.k / (2 * np.maximum(self.r, 1e-3)) * dt
        self.r = np.where(rel, np.sqrt(np.maximum(self.r ** 2 + 2 * self.r * dr, 0)), self.r)
        omega = 0.6 * np.maximum(self.r, 0.15) ** -1.5 * spin_in
        self.th = np.where(rel, self.th + omega * dt, self.th)
        before = self.alive.sum()
        self.alive &= ~(rel & (self.r < self.rh(t) * 1.02 + 0.004))
        self.eaten_now = (before - self.alive.sum()) / NP
        self.t += dt

    def advance_to(self, t):
        while self.t < t - 1e-9:
            self.step(min(1 / (FPS * 2), t - self.t))


def wall_positions(sim, t, rh):
    """3D-позиции букв до вспышки, яркость, цвет."""
    rel = t >= TAU
    heat = sstep(TAU, TAU + 1.5, t)
    flat = sstep(TAU, TAU + 2.5, t)
    phi = flat * (math.pi / 2)
    r, th = sim.r, sim.th
    # стена кода выгибается вокруг дыры, как через линзу
    rE = 1.5 * rh
    rl = np.where(rel, r, (r + np.sqrt(r ** 2 + 4 * rE ** 2)) / 2)
    # волны по коду на каждую долю
    wave = np.zeros(NP, np.float32)
    if t > T_HOLE:
        k0 = int((t - BEATO) // BEATP)
        for k in range(k0 - 2, k0 + 1):
            tb = BEATO + k * BEATP
            age = t - tb
            if tb < T_HOLE or age < 0:
                continue
            wave += math.exp(-age * 1.6) * np.exp(-((R0 - (0.04 + 0.8 * age)) / 0.06) ** 2)
    wave *= ~rel
    rl = rl + 0.02 * wave
    P = np.stack([rl * np.cos(th), rl * np.sin(th) * np.cos(phi), -rl * np.sin(th) * np.sin(phi)], 1)
    rgb = P_RGB * (1 - heat[:, None]) + temp_color(r) * heat[:, None]
    rgb = rgb + (np.array([255, 170, 90], np.float32) - rgb) * np.clip(wave * 0.6, 0, 0.7)[:, None]
    b = np.where(rel, 0.8 + 0.5 * heat, 0.78) * (1 + 0.8 * wave)
    # слёт в начале: из-за камеры и с разных сторон
    v = np.clip((t - FLY_S) / FLY_T, 0, 1)
    fly = v < 1
    if fly.any():
        e = 1 - (1 - v) ** 3
        P[fly] = fly_pos(e[fly], np.nonzero(fly)[0])
        cool = np.array([120, 90, 230], np.float32)
        rgb[fly] = P_RGB[fly] + (cool - P_RGB[fly]) * (1 - e[fly])[:, None]
        b[fly] = 0.78 + 0.5 * (1 - e[fly])
    return P, rgb, b, rel, heat, flat, fly, v


def fly_pos(e, ids):
    off = (1 - e) * 0.5
    a = FLY_A[ids] + (1 - e) * 1.6
    return np.stack([WX[ids] + off * np.cos(a), WY[ids] + off * np.sin(a), (1 - e) * FLY_Z[ids]], 1)


def explosion_pos(t):
    u = np.maximum(t - EX_S, 0)
    dist = EX_V / 0.35 * (1 - np.exp(-0.35 * u))
    ang = EX_A + 2.6 * dist ** 0.75 + 0.5 * u
    P = (dist * np.cos(ang))[:, None] * E1 + (dist * np.sin(ang))[:, None] * E2 + (EX_H * (1 + dist))[:, None] * EN
    return P, u


_P_RE, _U_RE = None, None


def _re_state():
    global _P_RE, _U_RE, D_RE, A_RE, T_EATP, K_RE
    if _P_RE is None:
        u = np.maximum(T_RE - EX_S, 0)
        D_RE = EX_V / 0.35 * (1 - np.exp(-0.35 * u))
        A_RE = EX_A + 2.6 * D_RE ** 0.75 + 0.5 * u
        q = np.clip(D_RE / np.percentile(D_RE, 98), 0, 1)
        T_EATP = T_RE + 0.8 + (T_EAT - T_RE - 0.8) * (0.25 + 0.75 * q ** 0.8) + rng.uniform(-0.2, 0.2, NP)
        T_EATP = np.minimum(T_EATP, T_EAT + 0.2)
        K_RE = (D_RE ** 2 - 0.004) / np.maximum(T_EATP - T_RE - 0.6, 0.3)
        _P_RE, _U_RE = True, u


def galaxy_pos(t):
    """Взрыв -> рукава летят наружу; после T_RE новая дыра затягивает их обратно по спирали."""
    if t < T_RE:
        P, u = explosion_pos(t)
        return P, u, np.ones(NP, bool), np.linalg.norm(P, axis=1)
    _re_state()
    v = t - T_RE
    ue = v - 0.6 * (1 - math.exp(-v / 0.6))  # плавный разворот
    r = np.sqrt(np.maximum(D_RE ** 2 - K_RE * ue, 0))
    ang = A_RE + 0.5 * v + 0.6 * (4 / K_RE) * (np.sqrt(D_RE) - np.sqrt(r))
    P = (r * np.cos(ang))[:, None] * E1 + (r * np.sin(ang))[:, None] * E2 + (EX_H * (1 + r))[:, None] * EN
    alive = t < T_EATP
    return P, _U_RE + v, alive, r


def rh2(t):
    """Радиус новой дыры: появляется на долю, растёт по мере еды, в конце исчезает."""
    if t < T_RE:
        return 0.0
    _re_state()
    frac = float(np.mean(T_EATP <= t))
    r = 0.05 * float(sstep(T_RE, T_RE + 0.6, t)) + 0.07 * frac
    return r * (1 - float(sstep(T_GONE0, T_GONE1, t)))


# ---------- кадр ----------
def render(sim):
    t = sim.t
    rh = sim.rh(t) if t < T_FLASH else rh2(t)
    cam = camera(t)
    zf = zoom(t) if (t < 3 or t > T_BACK) else 1.0
    size = int(np.clip(round(9 * zf), 9, 27))
    at, cw, ch = atlas(size)
    cols, rows = VW // cw, VH // ch
    x0, y0 = (VW - cols * cw) / 2, (VH - rows * ch) / 2
    col = np.zeros((rows, cols, 3), np.float32)
    nebula = 0.0
    bri = np.full((rows, cols), -1.0, np.float32)
    idx = np.zeros((rows, cols), np.int64)

    def splat(sx, sy, b, rgb, chs, fill=False):
        ci = np.floor((VW / 2 + sx * U0 - x0) / cw).astype(int)
        ri = np.floor((VH / 2 - sy * U0 - y0) / ch).astype(int)
        if fill:
            ci = np.concatenate([ci + 1, ci, ci + 1, ci])
            ri = np.concatenate([ri, ri + 1, ri + 1, ri])
            b = np.concatenate([b * 0.97, b * 0.97, b * 0.96, b])
            rgb = np.concatenate([rgb] * 4)
            chs = np.concatenate([chs] * 4)
        ok = (ci >= 0) & (ci < cols) & (ri >= 0) & (ri < rows) & (b > 0.02)
        ci, ri, b, rgb, chs = ci[ok], ri[ok], b[ok], rgb[ok], chs[ok]
        o = np.argsort(b)
        ri, ci, b, rgb, chs = ri[o], ci[o], b[o], rgb[o], chs[o]
        win = b > bri[ri, ci]
        bri[ri[win], ci[win]] = b[win]
        col[ri[win], ci[win]] = rgb[win] * np.minimum(b[win], 1.4)[:, None]
        idx[ri[win], ci[win]] = chs[win]

    hsx, hsy, hz = project(np.zeros((1, 3)), cam)
    hsx, hsy, hz = float(hsx[0]), float(hsy[0]), float(hz[0])
    rhs = F * rh / hz
    tens = float(sstep(T_TENSE, T_COLLAPSE - 0.1, t)) * (t < T_FLASH)
    pl = pulse(t) * (float(sstep(T_HOLE, T_HOLE + 0.4, t)) * (t < T_COLLAPSE) + float(sstep(T_RE, T_RE + 0.4, t)))

    # звёзды: дальний план, линзирование вокруг дыры, перед ударом тянутся к ней
    sx, sy, sz = project(ST, cam)
    dx, dy = sx - hsx, sy - hsy
    rs = np.hypot(dx, dy) + 1e-6
    rE = 1.7 * rhs
    k = (rs + np.sqrt(rs ** 2 + 4 * rE ** 2)) / 2 / rs
    sx, sy = hsx + dx * k, hsy + dy * k
    tw = 0.75 + 0.25 * np.sin(t * 2.5 + ST_PH)
    sb = ST_B * tw * 0.8 * (1 - 0.45 * tens) * (sz > 0.1)
    star_rgb = np.full((NSTAR, 3), 230, np.float32)
    if tens > 0.05:
        for j in range(1, 8):
            q = 0.05 * j * tens
            splat(sx + (hsx - sx) * q, sy + (hsy - sy) * q, sb * (0.75 ** j) * 2.0, star_rgb,
                  char_for((hsx - sx) * ch, (hsy - sy) * cw))
    splat(sx, sy, sb, star_rgb, np.where(ST_B > 0.6, I_STAR, I_DOT))

    if t < T_FLASH:
        P, rgb, b, rel, heat, flat, fly, v = wall_positions(sim, t, rh)
        px, py, pz = project(P, cam)
        vis = sim.alive & (pz > 0.08)
        # доплер: сторона диска, летящая к камере, ярче
        vel = np.stack([-np.sin(sim.th), np.zeros(NP), -np.cos(sim.th)], 1)
        towards = -(vel @ cam[3])
        dop = 1 + 0.55 * towards * heat * flat
        b = b * dop * (1 + 0.25 * pl) * (1 - 0.4 * tens * rel)
        behind = (pz > hz) & (np.hypot(px - hsx, py - hsy) < rhs * 1.05)
        b = np.where(behind | ~vis, 0, b)
        # свет задней части диска загибается дугой над дырой и под ней
        lens = vis & rel & (flat > 0.5) & (sim.r < 0.7)
        rho = (rh * 1.3 + 0.3 * (sim.r - rh)) * F / hz
        up = lens & (np.sin(sim.th) > 0)
        dn = lens & (np.sin(sim.th) <= 0)
        splat(hsx + rho[up] * np.cos(sim.th[up]), hsy + rho[up] * np.sin(sim.th[up]), 1.0 * b[up], rgb[up], P_CH[up])
        splat(hsx + 0.8 * rho[dn] * np.cos(sim.th[dn]), hsy - 0.8 * rho[dn] * np.abs(np.sin(sim.th[dn])),
              0.35 * b[dn], rgb[dn], P_CH[dn])
        # шлейфы у прилетающих букв
        if fly.any():
            ids = np.nonzero(fly & (v > 0))[0]
            for j in range(1, 5):
                vj = np.clip((t - 0.04 * j - FLY_S[ids]) / FLY_T, 0, 1)
                Pj = fly_pos(1 - (1 - vj) ** 3, ids)
                qx, qy, qz = project(Pj, cam)
                m = (vj > 0) & (qz > 0.08)
                splat(qx[m], qy[m], (0.5 * 0.7 ** j) * b[ids][m], rgb[ids][m],
                      char_for((px[ids] - qx)[m] * ch, (py[ids] - qy)[m] * cw))
        wallp = ~rel & ~fly
        splat(px[wallp], py[wallp], b[wallp], rgb[wallp], P_CH[wallp], fill=True)
        splat(px[~wallp], py[~wallp], b[~wallp], rgb[~wallp], P_CH[~wallp])
    else:
        P, u, alive2, dist = galaxy_pos(t)
        px, py, pz = project(P, cam)
        born = (t >= EX_S) & (pz > 0.08) & alive2
        if t >= T_RE:  # часть позади новой дыры закрыта ею
            born &= ~((pz > hz) & (np.hypot(px - hsx, py - hsy) < rhs * 1.05))
        bp = pulse(t)  # после удара галактика вспыхивает в такт
        # цвет рукава: у центра бело-горячий, дальше насыщенный, к концу темнее; на долю чуть сдвигается к соседу
        arm = ARM_COL[EX_ARM] + (ARM_COL[(EX_ARM + 1) % ARMS] - ARM_COL[EX_ARM]) * (0.25 * bp)
        hot = np.clip(1 - dist / 0.45, 0, 1) * np.clip(1 - u / 1.2, 0, 1)
        if t >= T_RE:  # у новой дыры буквы снова раскаляются
            hot = np.maximum(hot, np.clip(1 - dist / 0.35, 0, 1) * float(sstep(T_RE, T_RE + 1.0, t)))
        rgb = arm + (np.array([255, 245, 235], np.float32) - arm) * hot[:, None]
        rgb = rgb * (1 - 0.3 * np.clip((dist - 1.0) / 1.2, 0, 1))[:, None]
        fade = 1.0
        b = (1.25 - 0.35 * np.clip(u / 2.2, 0, 1)) * born * fade * (1 + 0.35 * bp)
        for j in range(4, 0, -1):
            Pj, uj, _, _ = galaxy_pos(t - 0.05 * j)
            qx, qy, qz = project(Pj, cam)
            m = born & (uj > 0)
            splat(qx[m], qy[m], (0.55 * 0.65 ** j) * b[m], rgb[m], char_for((px - qx)[m] * ch, (py - qy)[m] * cw))
        splat(px, py, b, rgb, P_CH)
        # блёстки: отдельные буквы вспыхивают белыми звёздочками
        tw = np.maximum(0, np.sin(t * 9 + EX_TWP)) ** 16
        m = EX_TW & born & (tw > 0.3) & (u > 0.25)
        splat(px[m], py[m], 2.0 * tw[m] * fade, np.full((m.sum(), 3), 255, np.float32), np.full(m.sum(), I_STAR))
        # туманность: мягкие цветные облака по следу рукавов
        nebula = np.zeros((rows, cols, 3), np.float32)
        gw, gh = max(cols // 6, 4), max(rows // 6, 4)
        ci = np.clip(((VW / 2 + px * U0 - x0) / (cols * cw) * gw).astype(int), 0, gw - 1)
        ri = np.clip(((VH / 2 - py * U0 - y0) / (rows * ch) * gh).astype(int), 0, gh - 1)
        acc = np.zeros((gh, gw, 3), np.float32)
        w = (b > 0.05)
        np.add.at(acc, (ri[w], ci[w]), rgb[w] * b[w, None])
        acc = acc / (acc.max() + 1e-6) * 255
        nb = Image.fromarray(acc.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)).resize((cols, rows), Image.BILINEAR)
        left = 1.0 if t < T_RE else float(np.mean(alive2))
        nebula = np.asarray(nb, np.float32) * 0.7 * left * float(sstep(T_FLASH + 0.2, T_FLASH + 0.9, t)) * (1 + 0.3 * bp)

    # горизонт, фотонное кольцо, вспышка, ударная волна
    gx = (np.arange(cols) * cw + x0 + cw / 2 - VW / 2) / U0
    gy = (VH / 2 - (np.arange(rows) * ch + y0 + ch / 2)) / U0
    GX, GY = np.meshgrid(gx - hsx, gy - hsy)
    d = np.hypot(GX, GY)
    if rh > 0.003:
        rr = rhs * (1 + 0.18 * pl) * (1 + 0.07 * tens * math.sin(t * 53) * math.sin(t * 31))
        width = 0.006 + 0.006 * pl
        ring = np.exp(-((d - rr * 1.06) / width) ** 2)
        ring *= 0.9 + 1.4 * pl + 2.0 * min(1.0, sim.eaten_now * 400) + 0.9 * tens * abs(math.sin(t * 47))
        m = ring > 0.25
        col[m] = np.maximum(col[m], np.array([255, 200, 120]) * np.minimum(ring[m], 1.3)[:, None])
        idx[m & (bri < 0)] = I_STAR
        bri[m] = np.maximum(bri[m], ring[m])
        hole = d < rr
        col[hole] = 0
        bri[hole] = -1
    fl = float(sstep(T_COLLAPSE + 0.25, T_FLASH, t)) * (1 - float(sstep(T_FLASH, T_FLASH + 0.45, t)))
    if fl > 0:
        glowc = np.exp(-d / (0.03 + 0.22 * fl))[..., None]
        col = col + np.array([255, 240, 220]) * np.minimum(2.5 * fl * glowc, 1.6)
        idx[bri < 0] = I_STAR
    if t >= T_FLASH:
        age = t - T_FLASH
        rsw = 1.7 * age
        # ударная волна раздваивается на красное и синее кольцо
        for off, c in ((0.0, (255, 70, 90)), (-0.05 - 0.03 * age, (70, 150, 255)), (-0.025, (255, 240, 230))):
            sw = np.exp(-((d - (rsw + off)) / 0.022) ** 2) * math.exp(-age * 1.2) * 0.95
            m = (sw > 0.15) & (bri < sw)
            col[m] = np.array(c) * sw[m][:, None]
            idx[m] = I_DOT
            bri[m] = sw[m]
        # лучи из центра в момент удара
        if age < 0.7:
            k = math.exp(-age * 5)
            for a_, l_ in zip(RAY_A, RAY_L):
                rr_ = np.linspace(0.04, l_ * (0.3 + 2.5 * age), 40)
                rx, ry = hsx + rr_ * math.cos(a_), hsy + rr_ * math.sin(a_)
                rb = k * 1.6 * (1 - rr_ / rr_[-1]) ** 0.7
                rc = np.tile(np.array([[255, 235, 210]], np.float32), (40, 1))
                splat(rx, ry, rb, rc, np.full(40, int(char_for(np.array([math.cos(a_) * ch]), np.array([math.sin(a_) * cw]))[0])))

    has = (bri >= 0) | (col.max(-1) > 20)
    g = at[idx] * has[:, :, None, None]
    base = BG + 0.10 * col + nebula
    img = base[:, :, None, None, :] + g[..., None] * (col[:, :, None, None, :] - base[:, :, None, None, :])
    img = img.transpose(0, 2, 1, 3, 4).reshape(rows * ch, cols * cw, 3)
    img8 = np.clip(img, 0, 255).astype(np.uint8)
    glow = np.asarray(Image.fromarray(img8).filter(ImageFilter.GaussianBlur(5)), np.float32)
    out = np.clip(img + 1.0 * glow, 0, 255).astype(np.uint8)
    canvas = np.zeros((VH, VW, 3), np.uint8)
    canvas[:] = BG.astype(np.uint8)
    iy, ix = int(y0), int(x0)
    canvas[iy:iy + out.shape[0], ix:ix + out.shape[1]] = out
    return canvas


# ---------- кадр «это программа»: редактор кода + окно с дырой ----------
WIN_W, WIN_H = 1040, 1100
WIN_Y = 470
_ide = {}


def ide_layers():
    if _ide:
        return _ide
    lines = clean_source()
    start = next(i for i, l in enumerate(lines) if l.startswith("def render("))
    lines = lines[start - 30:start + 60]
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 21)
    fb = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 21)
    seg = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
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
    dt.rectangle((0, 0, 250, 64), fill=(43, 43, 43))
    dt.rectangle((0, 60, 250, 64), fill=(74, 136, 199))
    dt.text((24, 18), "blackhole.py", font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24), fill=(200, 200, 200))
    run = Image.new("RGB", (VW, 250), (43, 43, 43))
    dr = ImageDraw.Draw(run)
    dr.rectangle((0, 0, VW, 46), fill=(60, 63, 65))
    dr.text((20, 9), "Run:   blackhole", font=seg, fill=(200, 200, 200))
    dr.text((20, 66), "> python blackhole.py", font=f, fill=C_TXT)
    dr.text((20, 100), f"particles: {NP}  |  3d camera  |  30 fps", font=f, fill=C_STR)
    title = Image.new("RGB", (WIN_W, 36), (243, 243, 243))
    dti = ImageDraw.Draw(title)
    dti.text((40, 7), "blackhole", font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18), fill=(20, 20, 20))
    dti.ellipse((12, 10, 28, 26), outline=(70, 120, 200), width=3)
    sym = ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 18)
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
    scroll = int(300 * (1 - math.cos(2 * math.pi * t / DURATION)) / 2)  # туда-обратно, петля без шва
    out.paste(e["code"].crop((0, scroll, VW, scroll + VH - 64 - 250)), (0, 64))
    out.paste(e["top"], (0, 0))
    out.paste(e["run"], (0, VH - 250))
    out.paste(Image.new("RGB", e["shadow"].size, (0, 0, 0)), (20 - 40, WIN_Y - 40 + 6), e["shadow"])
    out.paste(e["title"], (20, WIN_Y))
    # окно показывает середину кадра дыры
    s = WIN_W / VW
    ch_ = int(WIN_H / s)
    y0 = (VH - ch_) // 2
    win = Image.fromarray(frame[y0:y0 + ch_]).resize((WIN_W, WIN_H), Image.LANCZOS)
    out.paste(win, (20, WIN_Y + 36))
    return np.asarray(out)


def export(path, audio=None, audio_start=0.0, ide=True):
    sim = Sim()
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-ss", f"{audio_start:.3f}", "-t", str(DURATION), "-i", audio, "-map", "0:v", "-map", "1:a",
                "-af", f"afade=t=in:d=0.04,afade=t=out:st={DURATION - 0.12:.2f}:d=0.12",
                "-c:a", "aac", "-b:a", "192k", "-t", str(DURATION)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        sim.advance_to(i / FPS)
        fr = render(sim)
        if ide:
            fr = to_ide(fr, i / FPS)
        p.stdin.write(fr.tobytes())
        if i % 60 == 0:
            print(f"{i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("done:", path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--export")
    ap.add_argument("--audio")
    ap.add_argument("--audio-start", type=float, default=AUDIO_START)
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--out", default="stills")
    ap.add_argument("--plain", action="store_true", help="без редактора, дыра на весь экран")
    a = ap.parse_args()
    if a.still:
        os.makedirs(a.out, exist_ok=True)
        sim = Sim()
        for s in sorted(a.still):
            sim.advance_to(s)
            fr = render(sim)
            Image.fromarray(fr if a.plain else to_ide(fr, s)).save(f"{a.out}/t{s:05.2f}.png")
        print("stills ok", NP, "particles")
    elif a.export:
        export(a.export, a.audio, a.audio_start, ide=not a.plain)

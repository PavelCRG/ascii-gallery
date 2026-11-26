import argparse
import math
import os
import re
import string
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

COLS, ROWS = 200, 80
FPS = 30
DURATION = 29.9  # длина трека из тиктока
BG = np.array([20, 20, 24], np.float32)
CHARS = string.ascii_letters + string.digits + "#%&@$*+=<>/\\?"
PHRASE = "ПYTИH XYЕС0C "  # сердечко: буквы из разных алфавитов, читается как по-русски

rng = np.random.default_rng(7)


# ---------- шрифт -> атлас глифов ----------
def build_atlas(chars, size=9):
    font = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", size)
    cw = int(round(font.getlength("M")))
    asc, desc = font.getmetrics()
    ch = asc + desc + 1
    atlas = np.zeros((len(chars), ch, cw), np.float32)
    for i, c in enumerate(chars):
        im = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
        atlas[i] = np.clip(np.asarray(im, np.float32) / 255.0 * 1.25, 0, 1) ** 0.75
    return atlas, cw, ch


ALL_CHARS = CHARS + "+*.-|/\\( " + "".join(sorted(set(PHRASE) - set(CHARS) - {" "}))
ATLAS, CW, CH = build_atlas(ALL_CHARS)
I_PLUS, I_STAR, I_DOT, I_DASH, I_BAR = (ALL_CHARS.index(c) for c in "+*.-|")
I_SLASH, I_BSLASH = ALL_CHARS.index("/"), ALL_CHARS.index("\\")
PH_IDX = np.array([ALL_CHARS.index(c) for c in PHRASE])
W, H = COLS * CW, ROWS * CH
UNIT = H / 2  # пикселей на единицу экрана

# координаты клеток на экране (единица = половина высоты, y вверх)
_c = (np.arange(COLS) + 0.5 - COLS / 2) * CW / UNIT
_r = -(np.arange(ROWS) + 0.5 - ROWS / 2) * CH / UNIT
SX, SY = np.meshgrid(_c, _r)
RR, CC = np.meshgrid(np.arange(ROWS), np.arange(COLS), indexing="ij")
PHRASE_GRID = PH_IDX[(CC + RR * 5) % len(PHRASE)]

# узор радужки
IR_K = rng.integers(6, 70, 14)
IR_PH = rng.random(14) * 6.28
IR_A = rng.random(14) * 0.6 + 0.4

REVEAL = rng.permutation(ROWS * COLS).reshape(ROWS, COLS) / (ROWS * COLS)
HAIR_N = rng.random((ROWS, COLS))

# звёзды в 3D: летят навстречу, когда камера влетает
NS = 520
ST_XY = rng.uniform(-1, 1, (NS, 2)) * np.array([1.35, 1.1])
ST_Z = rng.random(NS)
ST_B = 0.45 + 0.55 * rng.random(NS)
ST_PH = rng.random(NS) * 6.28

# ---------- форма глаза ----------
L = 1.2          # полуширина глаза
A0, B0 = 0.50, 0.36  # высота верхнего / нижнего века при открытом глазе

NU = 70
U_UP = -0.93 + 1.93 * np.linspace(0, 1, NU) ** 0.8
LEN_UP = (0.07 + 0.25 * np.clip((U_UP + 0.5) / 1.5, 0, 1) ** 1.3) * (0.85 + 0.3 * rng.random(NU))
LEN_UP[::3] *= 1.15
ANG_UP = np.radians(118 - 98 * ((U_UP + 1) / 2) ** 1.1) + rng.normal(0, 0.05, NU)
NL = 26
U_LO = np.linspace(-0.35, 0.95, NL)
LEN_LO = (0.03 + 0.06 * np.clip((U_LO + 0.35) / 1.3, 0, 1)) * (0.8 + 0.4 * rng.random(NL))
ANG_LO = np.radians(-80 + 45 * ((U_LO + 0.35) / 1.3))

# ---------- сценарий, всё в долях трека (118 BPM) ----------
BEAT, BEAT0 = 0.508, 0.055


def BT(k):
    return BEAT0 + k * BEAT


OPEN0, OPEN1 = BT(1), BT(3)          # глаз открывается
SAC = BT(9)                           # один рывок в сторону + прищур
RET = BT(12)                          # медленный возврат
BLINK_T = BT(18)                      # одно моргание
ZOOM0, ZOOM1 = BT(23), BT(43)         # влёт в зрачок
HZ0, HZ1 = BT(52), BT(55)             # влёт в сердечко
MORPH0, MORPH1 = HZ1 - 0.25, 29.55    # символы складываются обратно в закрытый глаз

FIX = [(0.0, 0.0, 0.0, 0.07), (SAC, 0.17, -0.03, 0.07), (RET, 0.0, -0.02, 3 * BEAT)]
BLINKS = [BLINK_T]


def sstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def mix(a, b, k):
    k = np.asarray(k, np.float32)[..., None]
    return a * (1 - k) + b * k


def C(*rgb):
    return np.array(rgb, np.float32)


def gaze(t):
    px, py = 0.0, 0.0
    gx, gy, ts, dur = FIX[0][1], FIX[0][2], 0.0, FIX[0][3]
    for t0, x, y, d in FIX:
        if t0 <= t:
            px, py, gx, gy, ts, dur = gx, gy, x, y, t0, d
    u = min(1.0, (t - ts) / dur)
    if dur < 0.2:  # резкий рывок с маленьким отскоком
        e = 1 - (1 - u) ** 3
        w = (t - ts - dur)
        e += 0.07 * math.sin(w * 40) * math.exp(-w * 18) if w > 0 else 0.0
    else:  # плавное возвращение
        e = u * u * (3 - 2 * u)
    x = px + (gx - px) * e
    y = py + (gy - py) * e
    x += 0.0015 * math.sin(t * 23.0) + 0.001 * math.sin(t * 41.0 + 1)
    y += 0.001 * math.sin(t * 29.0 + 2)
    return x, y


def blink(t):
    b = 0.0
    for tb in BLINKS:
        b = max(b, float(sstep(tb, tb + 0.08, t) * (1 - sstep(tb + 0.11, tb + 0.30, t))))
    return b


def lids(x, opn, lt, lb):
    u = x / L
    q = np.clip(1 - u ** 2, 0, None)
    tilt = 0.09 * u
    top = q ** 0.85 * (1 - 0.18 * u)
    bot = q ** 1.2 * (1 + 0.15 * u)
    closed = tilt - 0.035 * q
    up = closed + opn * (A0 * lt * top + 0.035 * q)
    lo = closed - opn * (B0 * lb * bot - 0.035 * q) + opn * (1 - lb) * 0.12 * q * (0.6 + 0.4 * u)
    return up, lo, u, q, tilt, top


def brow_line(x, raise_):
    k = np.where(x < 0.55, 1.6, 0.85)
    bump = np.clip(1 - ((x - 0.55) / k) ** 2, -0.5, 1)
    yb = 0.80 + 0.17 * bump + raise_ * sstep(-0.3, 0.7, x)
    th = np.interp(x, [-1.1, -0.7, 0.55, 1.35], [0.17, 0.14, 0.10, 0.02])
    return yb, th


def hearts_field(x, y):
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3


def _char_for(ddx, ddy):
    ang = np.degrees(np.arctan2(ddy, ddx)) % 180
    return np.select([ang < 22, ang < 68, ang < 112, ang < 158],
                     [I_DASH, I_SLASH, I_BAR, I_BSLASH], I_DASH)


# ---------- камера ----------
Z0 = 0.80
ZMAX = 2.1 / 0.25


def camera(t):
    zp = float(sstep(ZOOM0, ZOOM1, t))
    hz = float(sstep(HZ0, HZ1, t))
    Z = Z0 * math.exp(math.log(ZMAX / Z0) * zp) * (1 + 0.012 * max(0.0, t - ZOOM1))
    Z *= math.exp(math.log(7.0) * hz)
    return zp, hz, Z


def star_depth_shift(t):
    zp, hz, Z = camera(t)
    return 0.025 * t + 0.30 * math.log(Z / Z0)


def stars(t):
    """Звёзды в клетках экрана: яркость и символ (-1 = нет звезды)."""
    S = star_depth_shift(t)
    v = (star_depth_shift(t + 1 / FPS) - S) * FPS  # скорость полёта
    z = 0.08 + 0.92 * ((ST_Z - S / 0.92) % 1.0)
    b = ST_B * (0.75 + 0.25 * np.sin(t * 3 + ST_PH))
    b = b * sstep(1.0, 0.55, z) * sstep(0.08, 0.14, z) + 0.12 * ST_B
    b = b * sstep(1.0, 0.92, z)
    pts_r, pts_c, pts_b, pts_ch = [], [], [], []

    def put(x, y, bb, chv):
        ci = np.floor(x * UNIT / CW + COLS / 2).astype(int)
        ri = np.floor(-y * UNIT / CH + ROWS / 2).astype(int)
        ok = (ci >= 0) & (ci < COLS) & (ri >= 0) & (ri < ROWS)
        pts_r.append(ri[ok]); pts_c.append(ci[ok]); pts_b.append(bb[ok]); pts_ch.append(chv[ok])

    sx, sy = ST_XY[:, 0] / z * 0.45, ST_XY[:, 1] / z * 0.45
    head = np.where((b > 0.7) & (z < 0.4), I_PLUS, np.where(b > 0.5, I_STAR, I_DOT))
    # хвосты при быстром полёте
    dz = min(0.3, abs(v) * 0.06)
    if dz > 0.004:
        for j in range(1, 9):
            zz = z + dz * j / 8
            tx, ty = ST_XY[:, 0] / zz * 0.45, ST_XY[:, 1] / zz * 0.45
            put(tx, ty, b * (1 - j / 9) * 0.8, _char_for((sx - tx) * CH, (sy - ty) * CW))
    put(sx, sy, b, head)
    big = (head == I_PLUS)
    dxc, dyc = CW / UNIT, CH / UNIT
    for ox, oy, chv in ((dxc, 0, I_DASH), (-dxc, 0, I_DASH), (0, dyc, I_BAR), (0, -dyc, I_BAR)):
        put(sx[big] + ox, sy[big] + oy, b[big] * 0.7, np.full(big.sum(), chv))

    R = np.concatenate(pts_r); Cc = np.concatenate(pts_c)
    Bv = np.concatenate(pts_b); Ch = np.concatenate(pts_ch)
    o = np.argsort(Bv)
    sb = np.zeros((ROWS, COLS), np.float32)
    sch = np.full((ROWS, COLS), -1, np.int32)
    sb[R[o], Cc[o]] = Bv[o]
    sch[R[o], Cc[o]] = Ch[o]
    return sb, sch


# ---------- кадр ----------
def core(t):
    """Цвет клеток, символы-переопределения (-1 = обычный текст), подсветка фона клетки."""
    opn = float(sstep(OPEN0, OPEN1, t)) * (1 - 0.97 * blink(t))
    sly = float(sstep(SAC, SAC + 0.4, t)) * (1 - 0.65 * float(sstep(11.3, 12.8, t)))
    lt = 0.92 - 0.17 * sly
    lb = 1.0 - 0.45 * sly
    braise = 0.10 * float(sstep(SAC + 0.05, SAC + 0.35, t))

    gx, gy = gaze(t)
    zp, hz, Z = camera(t)
    rp = 0.20 + 0.05 * float(sstep(11.3, 13.8, t))
    # после моргания зрачок чуть сужается, как от света
    rp *= 1 - 0.12 * float(sstep(BLINK_T + 0.2, BLINK_T + 0.45, t)) * (1 - float(sstep(BLINK_T + 0.8, BLINK_T + 2.3, t)))
    k = zp ** 0.3
    cx, cy = 0.04 * (1 - k) + gx * k, gy * k
    WX = cx + SX / Z
    WY = cy + SY / Z
    ovr = np.full((ROWS, COLS), -1, np.int32)
    tint = np.full((ROWS, COLS), 0.16, np.float32)

    up, lo, u, q, tilt, top = lids(WX, opn, lt, lb)
    inside = (np.abs(u) < 1) & (WY < up) & (WY > lo)
    ineye = np.abs(u) < 1

    # кожа
    n = 0.5 + 0.5 * np.sin(WX * 9 + np.sin(WY * 7) * 2) * np.sin(WY * 11 + WX * 3)
    col = C(242, 182, 146) * (0.86 + 0.14 * n)[..., None]
    blush = np.exp(-(((WX - 0.8) / 0.5) ** 2 + ((WY + 0.75) / 0.25) ** 2))
    col = mix(col, C(238, 140, 150), 0.45 * blush)

    # тени на веке
    crease = tilt + A0 * 0.92 * top + 0.10 * q + 0.02
    d_up = WY - up
    sh = sstep(crease + 0.16, up + 0.02, WY) * (0.5 + 0.5 * sstep(-0.7, 0.9, u)) * (WY > up)
    sh = sh * np.clip(1.4 - np.abs(u) * 0.5, 0, 1) * (np.abs(u) < 1.25)
    col = mix(col, C(150, 72, 108), 0.85 * sh)
    shimmer = np.exp(-(((WX + 0.05) / 0.35) ** 2 + ((d_up - 0.06) / 0.05) ** 2)) * (WY > up)
    col = mix(col, C(255, 205, 215), 0.5 * shimmer * opn)
    cl = np.exp(-((WY - crease) / 0.03) ** 2) * ineye
    col = mix(col, C(120, 60, 80), 0.5 * cl)
    yb, th = brow_line(WX, braise)
    hl = np.exp(-((WY - (yb - th / 2 - 0.07)) / 0.05) ** 2) * (WX > -0.6) * (WX < 1.3)
    col = mix(col, C(255, 225, 205), 0.45 * hl)

    # нижнее веко
    d_lo = lo - WY
    col = np.where(((d_lo > 0) & (d_lo < 0.03) & ineye)[..., None], C(196, 118, 110), col)
    ll = (d_lo > 0.01) & (d_lo < 0.04) & (u > 0.2) & (u < 1)
    col = np.where(ll[..., None], C(110, 60, 70), col)

    # белок
    sc = mix(C(246, 242, 240), C(232, 160, 155), sstep(0.78, 1.0, np.abs(u)))
    sc = mix(sc, C(240, 150, 150), sstep(-0.82, -0.98, u))
    sc = sc * (1 - 0.42 * sstep(0.16, 0.0, up - WY))[..., None]
    sc = mix(sc, C(240, 190, 185), sstep(0.03, 0.0, WY - lo))

    # радужка (большая, как в круглых линзах)
    dx, dy = WX - gx, WY - gy
    r = np.hypot(dx, dy)
    a = np.arctan2(dy, dx)
    R = 0.43
    streak = np.zeros_like(r)
    for kk, ph, am in zip(IR_K, IR_PH, IR_A):
        streak += am * np.sin(kk * a + ph + 3 * r)
    streak = 0.5 + 0.5 * np.tanh(streak / 1.6)
    ir = mix(C(120, 45, 8), C(255, 190, 45), streak)
    ir = mix(ir, C(255, 215, 95), sstep(rp * 2.2, rp, r) * 0.7)
    ir = ir * (1 - 0.85 * sstep(R * 0.84, R * 0.93, r))[..., None]
    iris = r < R

    # космос в зрачке
    pupil = r < rp
    px, py = dx / rp, dy / rp
    neb = 0.5 + 0.5 * np.sin(SX * 3.1 + t * 0.2) * np.sin(SY * 2.3 - t * 0.15)
    space = C(6, 6, 10) + C(28, 8, 36) * (neb ** 2)[..., None]
    sv = float(sstep(0.15, 0.6, zp))
    sb, sch = stars(t)
    space = space + C(255, 255, 255) * (sb * sv)[..., None]

    # сердечко бьётся в такт
    hv = float(sstep(0.3, 0.75, zp))
    ph = (t - BEAT0) % BEAT
    beat = 1 + 0.08 * math.exp(-(ph / 0.06) ** 2) + 0.08 * math.exp(-((ph - BEAT) / 0.03) ** 2)
    HS = 0.26 * beat
    hx = px / HS * 1.15
    hy = py / HS * 1.15 + 0.12
    kmin = np.full(hx.shape, 9.0, np.float32)
    for kk in np.linspace(1.0, 0.05, 24):
        ins = hearts_field(hx / kk, hy / kk) < 0
        kmin = np.where(ins, kk, kmin)
    inh = kmin <= 1.0
    shade = np.sqrt(np.clip(1 - np.minimum(kmin, 1) ** 2, 0, 1))
    hc = mix(C(235, 45, 120), C(255, 140, 200), shade)
    band = 0.5 + 0.5 * np.sin(hy * 7 + t * 0.8)
    hc = mix(hc, C(255, 205, 228), 0.25 * band * shade)
    gloss = np.exp(-(((hx + 0.45) / 0.22) ** 2 + ((hy - 0.55) / 0.15) ** 2))
    hc = mix(hc, C(255, 250, 252), np.clip(gloss * 1.3, 0, 1))
    halo = np.exp(-np.hypot(hx, hy - 0.1) * 1.6) * (~inh) * (0.7 + 0.3 * (beat - 1) / 0.08)
    space = space + C(200, 30, 120) * (halo * 0.6 * hv)[..., None]
    space = np.where(inh[..., None], mix(space, hc, hv * np.ones_like(r)), space)
    heart_on = inh & (hv > 0.3)

    pup = mix(C(8, 6, 6), space, float(sstep(0.05, 0.3, zp)) * np.ones_like(r))
    gl = np.exp(-(((dx + 0.45 * rp) / (0.5 * rp)) ** 2 + ((dy - 0.55 * rp) / (0.35 * rp)) ** 2))
    gl *= 1 - sstep(0.0, 0.25, zp)

    eye = np.where(pupil[..., None], pup, np.where(iris[..., None], ir, sc))
    eye = mix(eye, C(255, 255, 255), np.clip(gl * 1.4, 0, 1) * (r < R))
    # отражение окна в радужке (смещается вместе со взглядом)
    ix, iy = dx / R + 0.25 * gx / R, dy / R
    pane = (ix > -0.66) & (ix < -0.2) & (iy > 0.12) & (iy < 0.54)
    pane &= (np.abs(ix + 0.43) > 0.025) & (np.abs(iy - 0.33) > 0.025)
    refl = pane & (r < R * 0.9) & (r > rp * 1.05)
    eye = mix(eye, C(255, 250, 240), 0.22 * refl * (1 - float(sstep(0.0, 0.3, zp))))
    col = np.where(inside[..., None], eye, col)

    # подводка + стрелка
    lw = 0.028 + 0.02 * sstep(-0.2, 1.0, u)
    liner = (d_up >= 0) & (d_up < lw) & ineye
    p0 = np.array([L * 0.97, 0.09 * 0.97 + 0.01])
    p1 = np.array([L + 0.30, 0.09 + 0.19])
    v = p1 - p0
    s = np.clip(((WX - p0[0]) * v[0] + (WY - p0[1]) * v[1]) / (v @ v), 0, 1)
    dist = np.hypot(WX - (p0[0] + s * v[0]), WY - (p0[1] + s * v[1]))
    wing = dist < 0.04 * (1 - s) + 0.003
    col = np.where((liner | wing)[..., None], C(22, 12, 18), col)

    # бровь
    bm = (np.abs(WY - yb) < th / 2) & (WX > -1.12) & (WX < 1.36)
    edge = np.abs(WY - yb) / (th / 2 + 1e-6)
    hair = bm & (HAIR_N > 0.08 + 0.6 * edge ** 2)
    hcol = mix(C(48, 28, 26), C(105, 68, 55), HAIR_N * 0.5 + sstep(-0.6, -1.1, WX) * 0.5)
    col = np.where(hair[..., None], hcol, col)
    bch = np.where(WX < -0.75, I_BAR, np.where(WX < 0.5, I_SLASH, I_BSLASH))
    ovr = np.where(hair, bch, ovr)

    lash_cells(ovr, col, opn, lt, lb, Z, cx, cy)

    full = float(sstep(0.92, 1.0, zp))
    col = mix(col, space, full * np.ones_like(r))
    if full > 0.5:
        ovr[:] = -1

    vis = (pupil & inside & (zp > 0.05)) | (full > 0.5)
    star_ok = vis & (sch >= 0) & (sb * sv > 0.05) & ~heart_on
    ovr = np.where(star_ok, sch, ovr)
    ovr = np.where(vis & heart_on, PHRASE_GRID, ovr)
    tint = np.where(vis & heart_on, 0.10, tint)  # буквы фразы контрастнее
    return col, ovr, tint


def scene(t):
    """Кадр с петлёй: в конце клетки по одной перескакивают в первый кадр (закрытый глаз)."""
    if t <= MORPH0:
        return core(t)
    a = core(t)
    b = core(0.0)
    p = float(np.clip((t - MORPH0) / (MORPH1 - MORPH0), 0, 1))
    sw = REVEAL < p
    return (np.where(sw[..., None], b[0], a[0]), np.where(sw, b[1], a[1]), np.where(sw, b[2], a[2]))


def lash_cells(ovr, col, opn, lt, lb, Z, cx, cy):
    flip = 2 * opn - 1  # при моргании ресницы опускаются вниз
    pts_x, pts_y, ch_l = [], [], []

    def add(xb, yb, ln, a0, curl, thick):
        a0 = np.arctan2(np.sin(a0) * flip, np.cos(a0))
        a1 = a0 + curl
        s = np.linspace(0, 1, 60)[:, None]
        p1x = xb + 0.5 * ln * np.cos(a0)
        p1y = yb + 0.5 * ln * np.sin(a0)
        p2x = p1x + 0.5 * ln * np.cos(a1)
        p2y = p1y + 0.5 * ln * np.sin(a1)
        bx = (1 - s) ** 2 * xb + 2 * (1 - s) * s * p1x + s ** 2 * p2x
        by = (1 - s) ** 2 * yb + 2 * (1 - s) * s * p1y + s ** 2 * p2y
        tx = 2 * (1 - s) * (p1x - xb) + 2 * s * (p2x - p1x)
        ty = 2 * (1 - s) * (p1y - yb) + 2 * s * (p2y - p1y)
        chars = _char_for(tx * CW, ty * CW)
        for dxo in thick:
            m = (s[:, 0] <= dxo[1])
            pts_x.append((bx + dxo[0] / Z)[m])
            pts_y.append(by[m])
            ch_l.append(chars[m])

    xu = U_UP * L
    up, _, _, _, _, _ = lids(xu, opn, lt, lb)
    curl_up = (np.pi / 2 - ANG_UP) * 0.65 * np.sign(flip + 1e-6)
    cell = CW / UNIT
    add(xu, up + 0.015, LEN_UP, ANG_UP, curl_up, [(0, 1.0), (cell, 0.45)])
    xl = U_LO * L
    _, lo, _, _, _, _ = lids(xl, opn, lt, lb)
    add(xl, lo - 0.03, LEN_LO, ANG_LO, -0.25 * np.ones(NL), [(0, 1.0)])

    X = np.concatenate([p.ravel() for p in pts_x])
    Y = np.concatenate([p.ravel() for p in pts_y])
    CHR = np.concatenate([c.ravel() for c in ch_l])
    sx = (X - cx) * Z
    sy = (Y - cy) * Z
    ci = np.floor(sx * UNIT / CW + COLS / 2).astype(int)
    ri = np.floor(-sy * UNIT / CH + ROWS / 2).astype(int)
    ok = (ci >= 0) & (ci < COLS) & (ri >= 0) & (ri < ROWS)
    ri, ci, CHR = ri[ok], ci[ok], CHR[ok]
    ovr[ri, ci] = CHR
    col[ri, ci] = C(30, 16, 26)


class Text:
    def __init__(self):
        self.idx = rng.integers(0, len(CHARS), (ROWS, COLS))

    def step(self):
        m = rng.random((ROWS, COLS)) < 0.03
        self.idx[m] = rng.integers(0, len(CHARS), m.sum())


def render(t, text):
    col, ovr, tint = scene(t)
    idx = np.where(ovr >= 0, ovr, text.idx)
    g = ATLAS[idx]
    base = BG + tint[..., None] * col
    img = base[:, :, None, None, :] + g[..., None] * (col[:, :, None, None, :] - base[:, :, None, None, :])
    img = img.transpose(0, 2, 1, 3, 4).reshape(H, W, 3)
    img8 = np.clip(img, 0, 255).astype(np.uint8)
    glow = np.asarray(Image.fromarray(img8).filter(ImageFilter.GaussianBlur(4)), np.float32)
    return np.clip(img + 0.9 * glow, 0, 255).astype(np.uint8)


# ---------- вертикальный кадр: редактор кода + окно программы ----------
VW, VH = 1080, 1920
KW = {"def", "return", "import", "from", "for", "in", "if", "else", "elif", "while", "class",
      "and", "or", "not", "None", "True", "False", "lambda", "with", "as", "global"}
COL_TXT, COL_KW, COL_STR = (169, 183, 198), (204, 120, 50), (106, 135, 89)
COL_NUM, COL_COM, COL_FN = (104, 151, 187), (128, 128, 128), (255, 198, 109)
TOKEN = re.compile(r'(#.*$)|("[^"]*"|\'[^\']*\')|(\b\d+\.?\d*\b)|([A-Za-z_]\w*)|(\s+)|(.)')
_editor = {}


def clean_source():
    """Код этого файла без комментариев и строк документации — для фона в ролике."""
    import io
    import tokenize
    src = open(__file__, encoding="utf8").read()
    lines = src.splitlines()
    cut = {}  # номер строки -> позиция, с которой обрезать
    drop = set()
    prev = tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            r, c = tok.start
            cut[r - 1] = min(c, cut.get(r - 1, 10 ** 9))
        elif tok.type == tokenize.STRING and prev in (tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT):
            for r in range(tok.start[0] - 1, tok.end[0]):
                drop.add(r)
        if tok.type not in (tokenize.COMMENT, tokenize.NL):
            prev = tok.type
    out = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        if i in cut:
            stripped = line[:cut[i]].rstrip()
            if not stripped.strip():
                continue
            line = stripped
        out.append(line)
    return out


def editor_layers():
    if _editor:
        return _editor
    lines = clean_source()
    start = next(i for i, l in enumerate(lines) if l.startswith("def core("))
    lines = lines[start:start + 90]
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 21)
    fb = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 21)
    lh = 27
    gut = 66
    code = Image.new("RGB", (VW, lh * len(lines) + 40), (43, 43, 43))
    d = ImageDraw.Draw(code)
    d.rectangle((0, 0, gut - 8, code.height), fill=(49, 51, 53))
    for i, line in enumerate(lines):
        y = 10 + i * lh
        d.text((gut - 14, y), str(start + 1 + i), font=f, fill=(96, 99, 102), anchor="ra")
        x = gut + 6
        prev = ""
        for m in TOKEN.finditer(line):
            tok = m.group(0)
            if m.group(1):
                c, ft = COL_COM, f
            elif m.group(2):
                c, ft = COL_STR, f
            elif m.group(3):
                c, ft = COL_NUM, f
            elif m.group(4) and tok in KW:
                c, ft = COL_KW, fb
            elif m.group(4) and prev == "def":
                c, ft = COL_FN, f
            else:
                c, ft = COL_TXT, f
            d.text((x, y), tok, font=ft, fill=c)
            x += f.getlength(tok)
            if m.group(4):
                prev = tok
            if x > VW:
                break
    top = Image.new("RGB", (VW, 64), (60, 63, 65))
    dt = ImageDraw.Draw(top)
    dt.rectangle((0, 0, 190, 64), fill=(43, 43, 43))
    dt.rectangle((0, 60, 190, 64), fill=(74, 136, 199))
    dt.text((24, 18), "eye.py", font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24), fill=(200, 200, 200))
    run = Image.new("RGB", (VW, 250), (43, 43, 43))
    dr = ImageDraw.Draw(run)
    dr.rectangle((0, 0, VW, 46), fill=(60, 63, 65))
    dr.text((20, 9), "Run:   eye", font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22), fill=(200, 200, 200))
    dr.text((20, 66), "> python eye.py", font=f, fill=(169, 183, 198))
    dr.text((20, 100), "frame ok  |  200x80 chars  |  30 fps", font=f, fill=(106, 135, 89))
    title = Image.new("RGB", (1040, 36), (243, 243, 243))
    dti = ImageDraw.Draw(title)
    sf = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18)
    dti.text((40, 7), "eye", font=sf, fill=(20, 20, 20))
    dti.ellipse((12, 10, 28, 26), outline=(70, 120, 200), width=3)
    for i, sym in enumerate(("—", "☐", "✕")):
        dti.text((1040 - 140 + i * 46, 6), sym, font=ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 18), fill=(30, 30, 30))
    shadow = Image.new("L", (1040 + 80, 36 + 915 + 80), 0)
    ImageDraw.Draw(shadow).rectangle((40, 40, 40 + 1040, 40 + 36 + 915), fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    _editor.update(code=code, top=top, run=run, title=title, shadow=shadow)
    return _editor


def to_vertical(frame, t):
    e = editor_layers()
    out = Image.new("RGB", (VW, VH), (43, 43, 43))
    scroll = int(260 * (1 - math.cos(2 * math.pi * t / DURATION)) / 2)  # туда-обратно: петля без шва
    out.paste(e["code"].crop((0, scroll, VW, scroll + VH - 64 - 250)), (0, 64))
    out.paste(e["top"], (0, 0))
    out.paste(e["run"], (0, VH - 250))
    wy = 560
    black = Image.new("RGB", e["shadow"].size, (0, 0, 0))
    out.paste(black, (20 - 40, wy - 40 + 6), e["shadow"])
    out.paste(e["title"], (20, wy))
    out.paste(Image.fromarray(frame).resize((1040, 915), Image.LANCZOS), (20, wy + 36))
    return np.asarray(out)


# ---------- звук: «вжух» на влётах ----------
def make_sfx(path, sr=44100):
    n = int(DURATION * sr)
    outl = np.zeros(n, np.float32)
    outr = np.zeros(n, np.float32)
    srng = np.random.default_rng(11)
    zp_fill = ZOOM0 + 0.826 * (ZOOM1 - ZOOM0)  # зрачок заполняет экран
    for tp, pre, gain in ((zp_fill, 1.7, 0.55), (HZ1, 1.4, 0.6)):
        i0 = int((tp - pre) * sr)
        m = int((pre + 0.6) * sr)
        tau = np.arange(m) / sr - pre
        env = np.where(tau < 0, np.exp(tau / (pre * 0.35)), np.exp(-tau / 0.13)).astype(np.float32)
        for ch, out in ((0, outl), (1, outr)):
            x = srng.standard_normal(m).astype(np.float32)
            fc = 300 + 5200 * env
            al = 1 - np.exp(-2 * np.pi * fc / sr)
            y = np.zeros(m, np.float32)
            acc = 0.0
            for i in range(m):
                acc += al[i] * (x[i] - acc)
                y[i] = acc
            pan = 0.5 + 0.35 * np.sin(tau * 3 + ch * math.pi)
            y = y * env * pan
            y = y / (np.abs(y).max() + 1e-9) * gain
            e = min(n, i0 + m)
            out[i0:e] += y[: e - i0]
    st = np.stack([outl, outr], 1)
    st = np.clip(st, -1, 1)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def export(path, vertical, audio=None):
    text = Text()
    size = (VW, VH) if vertical else (W, H)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{size[0]}x{size[1]}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-i", audio, "-map", "0:v", "-map", "1:a",
                "-af", "volume=1.5,alimiter=limit=0.95:level=false",  # музыка на 50% громче
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(DURATION)]  # только музыка, без «вжух» (make_sfx не используется)
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        t = i / FPS
        f = render(t, text)
        if vertical:
            f = to_vertical(f, t)
        p.stdin.write(f.tobytes())
        text.step()
        if i % 60 == 0:
            print(f"{i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("done:", path)


def live():
    import time
    import tkinter as tk
    from PIL import ImageTk

    root = tk.Tk()
    root.title("eye")
    root.configure(bg="#141418")
    lbl = tk.Label(root, bd=0, bg="#141418")
    lbl.pack()
    state = {"t0": time.perf_counter(), "text": Text()}

    def restart(_=None):
        state["t0"] = time.perf_counter()

    def tick():
        t = (time.perf_counter() - state["t0"]) % DURATION  # крутится по кругу
        img = ImageTk.PhotoImage(Image.fromarray(render(t, state["text"])))
        lbl.configure(image=img)
        lbl.image = img
        state["text"].step()
        root.after(1, tick)

    root.bind("<space>", restart)
    root.bind("<Escape>", lambda e: root.destroy())
    tick()
    root.mainloop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--export")
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--audio", help="музыка под ролик")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--out", default="stills")
    args = ap.parse_args()
    if args.still:
        tx = Text()
        os.makedirs(args.out, exist_ok=True)
        for s in args.still:
            fr = render(s, tx)
            if args.vertical:
                fr = to_vertical(fr, s)
            Image.fromarray(fr).save(f"{args.out}/t{s:05.2f}.png")
        print("stills ok")
    elif args.export:
        export(args.export, args.vertical, args.audio)
    else:
        live()

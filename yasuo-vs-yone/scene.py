"""Background, effects, camera and per-frame compositing for the duel."""
import math
import numpy as np
import cairo
from scipy.ndimage import gaussian_filter
from core import *
from rig import *
from choreo import *

SUN_C = (540.0, 1060.0)
SUN_R = 360.0
RIM = hexc('#ffb27a')


# ------------------------------------------------------------------ camera
CAM = Track((0, (1.12, 540, 1260)), (2.2, (1.14, 540, 1260)), (3.4, (1.24, 540, 1270)), (4.4, (1.24, 540, 1270)),
            (4.9, (1.24, 540, 1255)), (7.6, (1.24, 540, 1255)), (8.3, (1.15, 540, 1265)), (8.8, (1.08, 540, 1260)), (11.2, (1.1, 540, 1260)),
            (13.0, (1.38, 540, 1265)), (13.12, (1.38, 540, 1265)), (13.34, (1.26, 540, 1260), 'o'),
            (16.3, (1.3, 540, 1260)), (17.6, (1.14, 540, 1250)), (20.0, (1.1, 540, 1245), 'o'))
SHAKES = [(tc, 16 * pw) for tc, x, y, pw in CLASHES] + [(PASS_X, 22), (XSLASH_T + 0.3, 20), (TORNADO_CUT, 8)]
PUNCH = [(tc, 0.05 * pw) for tc, x, y, pw in CLASHES] + [(PASS_X, 0.06), (XSLASH_T + 0.3, 0.05)]


def camera(t):
    z, fx, fy = CAM(t)
    for te, a in PUNCH:
        if t >= te:
            z *= 1 + a * math.exp(-(t - te) * 9)
    sx = sy = 0.0
    for te, a in SHAKES:
        if t >= te:
            k = a * math.exp(-(t - te) * 13)
            sx += k * math.sin(t * 91 + te * 7)
            sy += k * math.cos(t * 77 + te * 3)
    m = cairo.Matrix()
    m.translate(fx + sx, fy + sy)
    m.scale(z, z)
    m.translate(-fx, -fy)
    return m


# ------------------------------------------------------------------ background
def draw_sky(c, t):
    g = cairo.LinearGradient(0, -200, 0, 1500)
    for k, col in ((0, '#120a22'), (0.28, '#2c1240'), (0.5, '#6e2148'), (0.68, '#c0413f'), (0.8, '#ec7040'),
                   (1.0, '#ffb257')):
        g.add_color_stop_rgb(k, *hexc(col))
    c.rectangle(-400, -400, W + 800, H + 800)
    c.set_source(g)
    c.fill()
    # faint stars at the top
    for i in range(60):
        x, y = hash01(i, 1) * W, hash01(i, 2) * 520
        a = 0.25 + 0.35 * hash01(i, 3) * (0.6 + 0.4 * math.sin(t * 2 + i))
        c.arc(x, y, 1.2 + hash01(i, 4) * 1.3, 0, TAU)
        c.set_source_rgba(1, 0.95, 0.9, a * (1 - y / 600))
        c.fill()
    # the big setting sun
    glow(c, SUN_C[0], SUN_C[1], SUN_R * 2.1, (1.0, 0.6, 0.35), 0.55)
    rg = cairo.RadialGradient(SUN_C[0], SUN_C[1] - 60, 20, SUN_C[0], SUN_C[1], SUN_R)
    rg.add_color_stop_rgb(0, *hexc('#fff4d6'))
    rg.add_color_stop_rgb(0.55, *hexc('#ffd28e'))
    rg.add_color_stop_rgb(0.9, *hexc('#ffa25c'))
    rg.add_color_stop_rgb(1, *hexc('#ff8a4c'))
    c.arc(SUN_C[0], SUN_C[1], SUN_R, 0, TAU)
    c.set_source(rg)
    c.fill()
    # cloud streaks crossing the sun
    drift = t * 6
    for i, (y, h, x0, w, col, a) in enumerate(((820, 16, -120, 760, '#6a1f45', 0.85), (870, 10, 380, 820, '#7c2a4a', 0.7),
                                                (935, 22, -60, 640, '#5a1a3e', 0.9), (1000, 12, 520, 700, '#86314c', 0.6),
                                                (640, 14, 200, 900, '#4a163a', 0.8), (560, 9, -200, 600, '#3a1236', 0.7))):
        xx = x0 + drift * (1 + 0.3 * i) - 200
        rrect(c, xx, y, w, h, h / 2)
        c.set_source_rgba(*hexc(col), a)
        c.fill()
    # far Ionian spires
    c.move_to(-300, 1500)
    pts = [(-300, 1260), (-60, 1230), (20, 1150), (60, 1215), (120, 1190), (170, 1080), (215, 1170), (300, 1215),
           (390, 1240), (470, 1225), (560, 1250), (650, 1215), (720, 1160), (760, 1100), (800, 1175), (880, 1200),
           (960, 1120), (1010, 1060), (1060, 1150), (1150, 1210), (1400, 1240)]
    for p in pts:
        c.line_to(*p)
    c.line_to(1400, 1500)
    c.close_path()
    c.set_source_rgba(*hexc('#7a2c4c'), 0.9)
    c.fill()
    # pagoda on the far left spire
    px, py = 170, 1084
    for k in range(3):
        wv = 44 - k * 11
        yy = py - 18 - k * 20
        c.move_to(px - wv, yy + 6)
        c.line_to(px + wv, yy + 6)
        c.line_to(px + wv * 0.6, yy - 4)
        c.line_to(px - wv * 0.6, yy - 4)
        c.close_path()
        c.rectangle(px - wv * 0.45, yy + 6, wv * 0.9, 14)
    c.move_to(px, py - 92)
    c.line_to(px, py - 70)
    c.set_line_width(3)
    c.set_source_rgba(*hexc('#5e2040'), 1)
    c.stroke_preserve()
    c.fill()
    # mid range
    c.move_to(-300, 1600)
    for x in range(-300, 1420, 40):
        y = 1330 + 38 * math.sin(x * 0.006 + 1.2) + 20 * math.sin(x * 0.017 + 0.4)
        c.line_to(x, y)
    c.line_to(1400, 1600)
    c.close_path()
    c.set_source_rgb(*hexc('#48183a'))
    c.fill()
    # haze band
    hz = cairo.LinearGradient(0, 1250, 0, 1420)
    hz.add_color_stop_rgba(0, 1, 0.55, 0.4, 0)
    hz.add_color_stop_rgba(0.6, 1, 0.55, 0.4, 0.16)
    hz.add_color_stop_rgba(1, 1, 0.55, 0.4, 0)
    c.rectangle(-400, 1250, W + 800, 170)
    c.set_source(hz)
    c.fill()
    # near hills
    c.move_to(-300, 1700)
    for x in range(-300, 1420, 30):
        y = 1420 + 22 * math.sin(x * 0.009 + 2.0) + 8 * math.sin(x * 0.03)
        c.line_to(x, y)
    c.line_to(1400, 1700)
    c.close_path()
    c.set_source_rgb(*hexc('#2c1026'))
    c.fill()


def ridge_y(x):
    return 1468 + 10 * math.sin(x * 0.004 + 0.3) + 18 * (abs(x - 540) / 540) ** 2


def draw_ground(c, t):
    c.move_to(-300, H + 400)
    for x in range(-300, 1420, 20):
        c.line_to(x, ridge_y(x))
    c.line_to(1400, H + 400)
    c.close_path()
    g = cairo.LinearGradient(0, 1460, 0, 1920)
    g.add_color_stop_rgb(0, *hexc('#24101f'))
    g.add_color_stop_rgb(1, *hexc('#0c060c'))
    c.set_source(g)
    c.fill()
    # rim of the ridge catching the sun
    c.move_to(-300, ridge_y(-300))
    for x in range(-300, 1420, 20):
        c.line_to(x, ridge_y(x))
    c.set_source_rgba(*RIM, 0.35)
    c.set_line_width(3)
    c.stroke()


def draw_tree(c, t):
    sway = 0.012 * math.sin(t * 1.3) + wind(t) * 0.00003
    c.save()
    c.translate(1010, 1475)
    c.rotate(sway)
    # trunk + branches
    c.move_to(-26, 0)
    c.curve_to(-30, -180, -80, -320, -120, -470)
    c.curve_to(-140, -540, -170, -600, -210, -640)
    c.line_to(-196, -652)
    c.curve_to(-150, -610, -110, -560, -92, -500)
    c.curve_to(-60, -380, 10, -220, 22, 0)
    c.close_path()
    c.set_source_rgb(*hexc('#1c0c16'))
    c.fill()
    for (x0, y0, x1, y1, w) in ((-100, -430, -230, -520, 9), (-70, -330, 40, -470, 8), (-160, -600, -280, -610, 6)):
        c.move_to(x0, y0)
        c.curve_to((x0 + x1) / 2, y0 - 30, (x0 + x1) / 2, y1 + 10, x1, y1)
        c.set_line_width(w)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.stroke()
    # blossom clusters
    rng = np.random.default_rng(3)
    blobs = []
    for cx, cy, n, r in ((-200, -620, 16, 70), (-250, -520, 12, 60), (30, -480, 12, 60), (-110, -690, 10, 55),
                         (-30, -600, 12, 60), (-300, -600, 8, 45)):
        for k in range(n):
            a = rng.uniform(0, TAU)
            d = rng.uniform(0, r)
            blobs.append((cx + math.cos(a) * d, cy + math.sin(a) * d * 0.7, rng.uniform(18, 34), rng.random()))
    blobs.sort(key=lambda b: b[1])
    for x, y, r, k in blobs:
        wob = 2 * math.sin(t * 2 + x * 0.05)
        c.arc(x + wob, y, r, 0, TAU)
        col = mixc(hexc('#b04a78'), hexc('#f29ac0'), 0.3 + 0.7 * k)
        c.set_source_rgb(*col)
        c.fill()
    for x, y, r, k in blobs[::3]:
        c.arc(x - r * 0.3, y - r * 0.3, r * 0.45, 0, TAU)
        c.set_source_rgba(1, 0.85, 0.9, 0.35)
        c.fill()
    c.restore()
    # framing branch top-left
    c.save()
    c.move_to(-40, 360)
    c.curve_to(80, 330, 180, 300, 300, 250)
    c.set_line_width(12)
    c.set_source_rgb(*hexc('#1a0a14'))
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.stroke()
    c.move_to(120, 322)
    c.curve_to(150, 360, 190, 390, 230, 400)
    c.set_line_width(6)
    c.stroke()
    rng = np.random.default_rng(9)
    for k in range(34):
        x = rng.uniform(-20, 320)
        y = 360 - (x + 40) * 0.33 + rng.uniform(-40, 40)
        c.arc(x + 3 * math.sin(t * 2.2 + k), y, rng.uniform(12, 24), 0, TAU)
        c.set_source_rgb(*mixc(hexc('#8e3a66'), hexc('#e98ab4'), rng.random()))
        c.fill()
    c.restore()


# ------------------------------------------------------------------ petals
NP = 170
_rng = np.random.default_rng(21)
PETALS = [dict(x0=_rng.uniform(-100, 1180), y0=_rng.uniform(150, 1750), fall=_rng.uniform(25, 60),
               sw=_rng.uniform(10, 30), sf=_rng.uniform(0.6, 1.6), ph=_rng.uniform(0, TAU),
               spin=_rng.uniform(1.5, 4.5), size=_rng.uniform(5, 10), front=_rng.random() < 0.35,
               drift=_rng.uniform(0.6, 1.3), tone=_rng.random()) for _ in range(NP)]
_TD = np.arange(0, 20.6, 1 / 60)
_DRIFT = np.cumsum([wind(x) * (0.9 if x < 11.4 else 1) for x in _TD]) / 60
_SPD = np.array([ptime(x) for x in _TD])
BURSTS = [(tc, x, y, 170 * pw) for tc, x, y, pw in CLASHES] + [(TORNADO_CUT, 735, 1250, 260), (PASS_X, 540, 1260, 220),
                                                                 (XSLASH_T + 0.3, 540, 1170, 520), (3.5, 300, 1300, 150)]


def _drift(t):
    # wind drift is integrated in real time but scaled by the slow-motion factor
    return float(np.interp(t, _TD, _DRIFT)) * 0.35


def petal_base(p, t):
    pt = ptime(t)
    x = p['x0'] + _drift(t) * p['drift'] + p['sw'] * math.sin(pt * p['sf'] + p['ph'])
    y = p['y0'] + p['fall'] * pt + 8 * math.sin(pt * p['sf'] * 1.3 + p['ph'] * 2)
    x = (x + 100) % 1280 - 100
    y = (y - 150) % 1650 + 150
    return x, y


def petal_pos(p, t):
    x, y = petal_base(p, t)
    for te, ex, ey, st in BURSTS:
        if t > te:
            bx, by = petal_base(p, te)
            dx, dy = bx - ex, by - ey
            d = math.hypot(dx, dy) + 1
            fall = math.exp(-d / 260)
            k = (1 - math.exp(-(ptime(t) - ptime(te)) * 3.0)) * st * fall
            x += dx / d * k
            y += dy / d * k - k * 0.4
    return x, y


def draw_petals(c, t, front):
    pt = ptime(t)
    for i, p in enumerate(PETALS):
        if p['front'] != front:
            continue
        x, y = petal_pos(p, t)
        sz = p['size'] * (1.6 if front else 1.0)
        ang = pt * p['spin'] + p['ph']
        c.save()
        c.translate(x, y)
        c.rotate(ang)
        c.scale(sz, sz * (0.35 + 0.65 * abs(math.cos(pt * p['spin'] * 0.7 + p['ph']))))
        c.move_to(-1, 0)
        c.curve_to(-0.6, -0.7, 0.5, -0.7, 1, -0.1)
        c.line_to(0.8, 0.1)
        c.curve_to(0.4, 0.6, -0.6, 0.6, -1, 0)
        c.restore()
        col = mixc(hexc('#f38fb5'), hexc('#ffd6e6'), p['tone'])
        c.set_source_rgba(*col, 0.95 if front else 0.85)
        c.fill()


# ------------------------------------------------------------------ grass
_grng = np.random.default_rng(33)
GRASS = [dict(x=_grng.uniform(-80, 1160), row=r, h=_grng.uniform(30, 70) + r * 22, w=_grng.uniform(4, 8),
              ph=_grng.uniform(0, TAU), lean=_grng.uniform(-0.2, 0.2)) for r in range(3) for _ in range(95)]


def grass_push(x, t):
    push = 0.0
    for te, ex, ey, pw in CLASHES:
        if t > te:
            push += 0.6 * pw * math.exp(-(t - te) * 4) * math.exp(-abs(x - ex) / 200) * (1 if x > ex else -1)
    if t > PASS_X:
        push += 0.9 * math.exp(-(t - PASS_X) * 3) * math.exp(-abs(x - 540) / 260) * (1 if x > 540 else -1)
    if t > XSLASH_T + 0.3:
        push += 1.0 * math.exp(-(t - XSLASH_T - 0.3) * 2.5) * math.exp(-abs(x - 540) / 360) * (1 if x > 540 else -1)
    # tornado
    if TORNADO_T0 < t < TORNADO_CUT + 0.3:
        tx = tornado_x(t)
        push += 0.8 * math.exp(-abs(x - tx) / 90) * math.sin(t * 20 + x * 0.05)
    return push


def draw_grass(c, t, rows):
    w = wind(t)
    for g in GRASS:
        if g['row'] not in rows:
            continue
        x = g['x']
        base = ridge_y(x) + 6 + g['row'] * 34
        bend = g['lean'] + w * 0.0012 + 0.12 * math.sin(t * 2.6 + g['ph'] + x * 0.01) + grass_push(x, t)
        h = g['h']
        tipx = x + math.sin(bend) * h
        tipy = base - math.cos(bend) * h
        mx = x + math.sin(bend * 0.5) * h * 0.5
        my = base - math.cos(bend * 0.5) * h * 0.55
        c.move_to(x - g['w'], base)
        c.curve_to(mx - g['w'] * 0.5, my, mx, my, tipx, tipy)
        c.curve_to(mx + g['w'] * 0.3, my, mx + g['w'] * 0.5, my, x + g['w'], base)
        c.close_path()
        shade_k = 0.06 * g['row']
        c.set_source_rgb(*mixc(hexc('#2a1224'), hexc('#0c050b'), 0.3 + shade_k * 4))
        c.fill()
        if g['row'] == 0:
            c.move_to(mx, my)
            c.line_to(tipx, tipy)
            c.set_source_rgba(*RIM, 0.28)
            c.set_line_width(1.5)
            c.stroke()


# ------------------------------------------------------------------ fx helpers
def bloom_composite(dst, surf, strength=1.0):
    surf.flush()
    buf = np.ndarray((H, W, 4), np.uint8, surf.get_data())
    small = buf.reshape(SH, 8, SW, 8, 4).mean(axis=(1, 3)).astype(np.float32)
    if small[..., 3].max() <= 0:
        return
    for sig, gain in ((1.2, 1.3), (4.0, 1.0)):
        b = gaussian_filter(small, (sig, sig, 0)) * gain * strength
        arr = np.clip(b, 0, 255).astype(np.uint8)
        arr[..., 3] = np.maximum(arr[..., 3], arr[..., :3].max(axis=2))
        ms = cairo.ImageSurface.create_for_data(arr, cairo.FORMAT_ARGB32, SW, SH)
        dst.save()
        dst.identity_matrix()
        dst.scale(W / SW, H / SH)
        p = cairo.SurfacePattern(ms)
        p.set_filter(cairo.FILTER_BILINEAR)
        p.set_extend(cairo.EXTEND_PAD)
        dst.set_source(p)
        dst.set_operator(cairo.OPERATOR_ADD)
        dst.paint()
        dst.restore()
    dst.save()
    dst.identity_matrix()
    dst.set_source_surface(surf, 0, 0)
    dst.set_operator(cairo.OPERATOR_ADD)
    dst.paint()
    dst.restore()


def rim_composite(dst, surf, off, alpha=1.0, rim_a=0.9):
    dst.save()
    dst.identity_matrix()
    dst.set_source_rgba(*RIM, rim_a * alpha)
    dst.mask_surface(surf, off[0], off[1])
    dst.set_source_surface(surf, 0, 0)
    dst.paint_with_alpha(alpha)
    dst.restore()


def rim_offset(J, cam):
    d = vnorm(vsub(SUN_C, J['chest']))
    return (d[0] * 3.2, d[1] * 2.0)


# ------------------------------------------------------------------ blades + trails
def blade_list(who, t):
    if who == 'yasuo':
        p = YAS(t)
        dr = drawn_yasuo(t)
        J = solve(p)
        return [(J['haN'], J['sN'], BLADES['yasuo'][0])] if dr[0] else []
    if who == 'spirit':
        p = SPI(t)
        J = solve(p)
        return [(J['haN'], J['sN'], BLADES['yone'][0]), (J['haF'], J['sF'], BLADES['yone'][1])]
    p = YON(t)
    J = solve(p)
    dr = drawn_yone(t)
    out = []
    if dr[0]:
        out.append((J['haN'], J['sN'], BLADES['yone'][0]))
    if dr[1]:
        out.append((J['haF'], J['sF'], BLADES['yone'][1]))
    return out


def draw_trails(c, who, t, alpha=1.0):
    n = 9
    dt = 1 / 110
    samples = [blade_list(who, t - k * dt) for k in range(n)]
    nb = len(samples[0])
    for b in range(nb):
        pts = []
        for k in range(n):
            if len(samples[k]) <= b:
                break
            hnd, ang, bl = samples[k][b]
            base, tip, d, nn = blade_points(hnd, ang)
            pts.append((vadd(base, d, BLADE * 0.5), tip))
        if len(pts) < 3:
            continue
        # only real swings leave a trail (not a blade that is just carried around)
        mv = vlen(vsub(pts[0][1], pts[-1][1]))
        a0 = samples[0][b][1]
        a1 = samples[len(pts) - 1][b][1]
        turn = abs(a0 - a1)
        if mv < 40 or turn < 30:
            continue
        mv = min(mv, turn * 6)
        col = samples[0][b][2]['glow']
        for k in range(len(pts) - 1):
            a = (1 - k / (len(pts) - 1)) ** 1.6 * alpha * clamp((mv - 40) / 120)
            (b0, t0), (b1, t1) = pts[k], pts[k + 1]
            c.move_to(*b0)
            c.line_to(*t0)
            c.line_to(*t1)
            c.line_to(*b1)
            c.close_path()
            c.set_source_rgba(*mixc(col, (1, 1, 1), 0.35 * (1 - k / n)), 0.38 * a)
            c.fill()
        # bright edge along the tip path
        c.move_to(*pts[0][1])
        for _, tp in pts[1:]:
            c.line_to(*tp)
        c.set_source_rgba(1, 1, 1, 0.6 * alpha * clamp((mv - 40) / 120))
        c.set_line_width(3)
        c.stroke()


# ------------------------------------------------------------------ clash fx
def draw_clash_fx(c, t):
    """Into the additive FX layer: sparks + impact stars."""
    for idx, (tc, x, y, pw) in enumerate(CLASHES):
        if not (tc <= t < tc + 0.8):
            continue
        a = t - tc
        rng = np.random.default_rng(100 + idx)
        n = int(44 * pw)
        for i in range(n):
            ang = rng.uniform(0, TAU)
            sp = rng.uniform(350, 1250) * (0.6 + 0.4 * pw)
            life = rng.uniform(0.25, 0.6)
            if a > life:
                continue
            vx, vy = math.cos(ang) * sp, math.sin(ang) * sp - 200
            px = x + vx * a
            py = y + vy * a + 0.5 * 2200 * a * a
            qx, qy = vx, vy + 2200 * a
            L = 0.022
            k = 1 - a / life
            c.move_to(px, py)
            c.line_to(px - qx * L, py - qy * L)
            c.set_source_rgba(1, lerp(0.55, 0.95, k), lerp(0.2, 0.7, k), k)
            c.set_line_width(2.6 * k + 0.6)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.stroke()
        if a < 0.14:
            k = 1 - a / 0.14
            for i in range(8):
                ang = i * TAU / 8 + idx
                L = (170 if i % 2 == 0 else 90) * pw * (0.6 + 0.4 * k)
                w = 7 * k
                c.move_to(x + math.cos(ang + 1.57) * w, y + math.sin(ang + 1.57) * w)
                c.line_to(x + math.cos(ang) * L, y + math.sin(ang) * L)
                c.line_to(x - math.cos(ang + 1.57) * w, y - math.sin(ang + 1.57) * w)
                c.close_path()
                c.set_source_rgba(1, 0.97, 0.85, k)
                c.fill()
    # grinding sparks while the blades are locked
    if 5.1 <= t < 5.5:
        rng = np.random.default_rng(int(t * 60))
        for i in range(6):
            ang = rng.uniform(-2.8, -0.3)
            L = rng.uniform(20, 70)
            x, y = 541 + rng.uniform(-4, 4), 1176 + rng.uniform(-4, 4)
            c.move_to(x, y)
            c.line_to(x + math.cos(ang) * L, y + math.sin(ang) * L)
            c.set_source_rgba(1, 0.85, 0.5, 0.9)
            c.set_line_width(2)
            c.stroke()


def draw_clash_glows(ctx, t):
    for tc, x, y, pw in CLASHES:
        if tc <= t < tc + 0.5:
            a = t - tc
            glow(ctx, x, y, 320 * pw * (0.6 + a * 2), (1, 0.92, 0.75), 0.9 * pw * math.exp(-a * 9), op=cairo.OPERATOR_ADD)
            # shockwave
            k = seg(a, 0, 0.32)
            if k < 1:
                ctx.save()
                ctx.translate(x, y)
                ctx.scale(1, 0.55)
                ctx.arc(0, 0, 40 + 300 * pw * e_o(k), 0, TAU)
                ctx.restore()
                ctx.set_source_rgba(1, 0.95, 0.85, 0.7 * (1 - k))
                ctx.set_line_width(7 * (1 - k) + 1)
                ctx.stroke()
    if 5.08 <= t < 5.5:
        glow(ctx, 541, 1176, 90, (1, 0.8, 0.5), 0.35 + 0.1 * math.sin(t * 60), op=cairo.OPERATOR_ADD)


# ------------------------------------------------------------------ wind / tornado / spirit / slashes
def draw_wind_swirls(c, t):
    k = 0.0
    k = max(k, math.sin(math.pi * seg(t, 3.45, 4.3)))
    k = max(k, math.sin(math.pi * seg(t, 8.5, 9.45)) * 1.2)
    if k <= 0.01:
        return
    J = solve(YAS(t))
    cx, cy = J['hip'][0], J['hip'][1] - 60
    for i in range(6):
        ry = 60 + i * 26
        rx = 95 + i * 8
        a0 = t * (6 + i) + i * 1.3
        c.save()
        c.translate(cx, cy - 40 + i * 22 - 60)
        c.scale(1, 0.24)
        c.arc(0, 0, rx, a0, a0 + 2.2)
        c.restore()
        c.set_source_rgba(0.55, 0.9, 1.0, 0.55 * k)
        c.set_line_width(3)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.stroke()


def tornado_x(t):
    return lerp(410, 735, e_io(seg(t, TORNADO_T0, TORNADO_CUT)) * 0.4 + seg(t, TORNADO_T0, TORNADO_CUT) * 0.6)


def draw_tornado(c, t):
    if not (TORNADO_T0 <= t < TORNADO_CUT + 0.5):
        return
    grow = e_o(seg(t, TORNADO_T0, TORNADO_T0 + 0.25))
    cut = seg(t, TORNADO_CUT, TORNADO_CUT + 0.45)
    x0 = tornado_x(t)
    if cut < 1:
        for half in ((0, 1) if cut > 0 else (None,)):
            off = 0 if half is None else (-1 if half == 0 else 1) * 120 * e_o(cut)
            c.move_to(x0 - 26 + off, G)
            c.curve_to(x0 - 40 + off, G - 200 * grow, x0 - 120 + off, G - 330 * grow, x0 - 150 + off + 20 * math.sin(t * 5), G - 440 * grow)
            c.line_to(x0 + 150 + off + 20 * math.sin(t * 5), G - 440 * grow)
            c.curve_to(x0 + 120 + off, G - 330 * grow, x0 + 40 + off, G - 200 * grow, x0 + 26 + off, G)
            c.close_path()
            fg = cairo.LinearGradient(0, G, 0, G - 440)
            fg.add_color_stop_rgba(0, 0.7, 0.92, 1.0, 0.3 * (1 - cut))
            fg.add_color_stop_rgba(1, 0.7, 0.92, 1.0, 0.05 * (1 - cut))
            c.set_source(fg)
            c.fill()
    for j in range(14):
        y = G - 8 - j * 31 * grow
        r = (30 + j * 9.5) * grow
        lean = 14 * math.sin(t * 5 + j * 0.4) + j * 2
        for half in (0, 1):
            off = (-1 if half == 0 else 1) * 120 * e_o(cut)
            rise = -80 * e_o(cut) * (1 if half else 0.6)
            for s in range(2):
                a0 = t * 16 + j * 0.9 + s * math.pi + half * math.pi / 2
                c.save()
                c.translate(x0 + lean + off, y + rise)
                c.scale(1, 0.26)
                if cut > 0:
                    c.arc(0, 0, r, a0, a0 + 1.6)
                else:
                    c.arc(0, 0, r, a0, a0 + 2.4)
                c.restore()
                c.set_source_rgba(0.75, 0.95, 1.0, (0.55 - 0.02 * j) * (1 - cut))
                c.set_line_width(3.5 - j * 0.12)
                c.set_line_cap(cairo.LINE_CAP_ROUND)
                c.stroke()
            if cut <= 0:
                break


def draw_xcut(c, t):
    k = seg(t, TORNADO_CUT - 0.02, TORNADO_CUT + 0.35)
    if not (0 < k < 1):
        return
    x, y = 735, 1250
    grow = e_o(seg(k, 0, 0.3))
    a = 1 - e_i(seg(k, 0.3, 1))
    for (ang, col) in ((-50, hexc('#ff3a4c')), (50, hexc('#4aa8ff'))):
        d = adir(ang)
        L = 230 * grow
        p0 = (x - d[0] * L, y - d[1] * L)
        p1 = (x + d[0] * L, y + d[1] * L)
        n = perp(d)
        c.move_to(*p0)
        c.curve_to(*vadd(vadd(p0, d, L * 0.6), n, 26), *vadd(vadd(p1, d, -L * 0.6), n, 26), *p1)
        c.curve_to(*vadd(vadd(p1, d, -L * 0.6), n, 12), *vadd(vadd(p0, d, L * 0.6), n, 12), *p0)
        c.close_path()
        c.set_source_rgba(*mixc(col, (1, 1, 1), 0.4), a)
        c.fill()


def draw_spirit_tether(c, t):
    a = spirit_alpha(t)
    if a <= 0:
        return
    Js = solve(SPI(t))
    Jb = solve(YON(t))
    p0, p1 = Js['chest'], Jb['chest']
    c.move_to(*p0)
    n = 12
    for i in range(1, n + 1):
        k = i / n
        x = lerp(p0[0], p1[0], k)
        y = lerp(p0[1], p1[1], k) + 10 * math.sin(k * 9 + t * 30) * math.sin(math.pi * k)
        c.line_to(x, y)
    c.set_source_rgba(0.5, 0.8, 1.0, 0.7 * a)
    c.set_line_width(3)
    c.stroke()


def draw_pass_streaks(c, t):
    if not (PASS_T0 <= t < PASS_T1 + 0.6):
        return
    k = seg(t, PASS_T0, PASS_T1)
    fade = 1 - seg(t, PASS_T1, PASS_T1 + 0.6)
    for (x0, x1, y, col) in ((330, 740, 1236, hexc('#7fd6ff')), (750, 340, 1262, hexc('#ff4a5c'))):
        xe = lerp(x0, x1, e_o(k))
        c.move_to(x0, y)
        c.line_to(xe, y - 3)
        c.line_to(xe, y + 3)
        c.close_path()
        c.set_source_rgba(*mixc(col, (1, 1, 1), 0.5), fade)
        c.fill()
        c.move_to(x0, y)
        c.line_to(xe, y)
        c.set_source_rgba(*col, 0.5 * fade)
        c.set_line_width(14)
        c.stroke()


def draw_big_x(c, t):
    t0 = XSLASH_T
    if not (t0 <= t < t0 + 1.4):
        return
    grow = e_o(seg(t, t0, t0 + 0.14))
    shatter = seg(t, t0 + 0.3, t0 + 1.3)
    ctr = (540, 1170)
    for idx, (ang, col) in enumerate(((42, hexc('#7fd6ff')), (-42, hexc('#ff3a4c')))):
        d = adir(ang)
        n = perp(d)
        L = 380 * grow
        if shatter <= 0:
            flick = 0.85 + 0.15 * math.sin(t * 90 + idx)
            p0 = (ctr[0] - d[0] * L, ctr[1] - d[1] * L)
            p1 = (ctr[0] + d[0] * L, ctr[1] + d[1] * L)
            c.move_to(*p0)
            c.line_to(*vadd(ctr, n, 9))
            c.line_to(*p1)
            c.line_to(*vadd(ctr, n, -9))
            c.close_path()
            c.set_source_rgba(*mixc(col, (1, 1, 1), 0.55), flick)
            c.fill()
            c.move_to(*p0)
            c.line_to(*p1)
            c.set_source_rgba(*col, 0.45)
            c.set_line_width(26)
            c.stroke()
        else:
            rng = np.random.default_rng(700 + idx)
            for s in range(34):
                u = rng.uniform(-1, 1)
                base = vadd(ctr, d, u * 380)
                v = (rng.uniform(-1, 1) * 420, rng.uniform(-1, 0.4) * 420)
                a = shatter
                px = base[0] + v[0] * a
                py = base[1] + v[1] * a + 300 * a * a
                sz = rng.uniform(6, 16) * (1 - a)
                rot = rng.uniform(0, TAU) + a * rng.uniform(-8, 8)
                c.move_to(px + math.cos(rot) * sz, py + math.sin(rot) * sz)
                c.line_to(px + math.cos(rot + 2.3) * sz * 0.5, py + math.sin(rot + 2.3) * sz * 0.5)
                c.line_to(px + math.cos(rot + 3.9) * sz * 0.6, py + math.sin(rot + 3.9) * sz * 0.6)
                c.close_path()
                c.set_source_rgba(*mixc(col, (1, 1, 1), 0.4), 1 - a)
                c.fill()


def draw_big_x_glow(ctx, t):
    t0 = XSLASH_T
    if t0 <= t < t0 + 1.0:
        k = t - t0
        glow(ctx, 540, 1170, 520, (1, 0.9, 0.8), 0.55 * math.exp(-k * 4), op=cairo.OPERATOR_ADD)
    if t0 + 0.3 <= t < t0 + 0.8:
        k = seg(t, t0 + 0.3, t0 + 0.8)
        ctx.save()
        ctx.translate(540, 1170)
        ctx.scale(1, 0.6)
        ctx.arc(0, 0, 60 + 560 * e_o(k), 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(1, 0.95, 0.9, 0.7 * (1 - k))
        ctx.set_line_width(8 * (1 - k) + 1)
        ctx.stroke()
    if PASS_X - 0.02 <= t < PASS_X + 0.5:
        k = t - PASS_X
        glow(ctx, 540, 1250, 600, (1, 1, 0.95), 0.95 * math.exp(-max(0, k) * 7), op=cairo.OPERATOR_ADD)


def draw_dust(c, t):
    events = [(4.55, 330, 1), (4.55, 760, -1), (7.08, 470, 1), (8.2, 285, -1), (PASS_T0, 332, 1), (PASS_T0, 750, -1),
              (PASS_T1, 740, 1), (PASS_T1, 340, -1), (TORNADO_T0, 420, 1), (0.9, 790, 0)]
    for k in range(8):
        events.append((7.72 + k * 0.05, lerp(670, 800, k / 7) + 30, -1))
    for te, x, dirx in events:
        a = t - te
        if not (0 <= a < 0.9):
            continue
        for i in range(5):
            r = (14 + 30 * e_o(a / 0.9)) * (0.7 + 0.1 * i)
            px = x - dirx * (10 + i * 12) * e_o(a / 0.9) + (i - 2) * 10
            py = G - 8 - i * 3 - 22 * e_o(a / 0.9)
            c.arc(px, py, r, 0, TAU)
            c.set_source_rgba(0.55, 0.32, 0.3, 0.32 * (1 - a / 0.9))
            c.fill()


def draw_speedlines(ctx, t):
    wins = [(4.5, 5.0, 1), (PASS_T0 - 0.02, PASS_T1 + 0.12, 0), (10.3, 10.56, -1)]
    for t0, t1, d in wins:
        if not (t0 <= t < t1):
            continue
        k = math.sin(math.pi * seg(t, t0, t1))
        rng = np.random.default_rng(int(t * 30))
        ctx.save()
        ctx.identity_matrix()
        for i in range(26):
            y = rng.uniform(950, 1560)
            x = rng.uniform(-100, W)
            L = rng.uniform(120, 420)
            ctx.move_to(x, y)
            ctx.line_to(x + L, y)
            ctx.set_source_rgba(1, 0.95, 0.9, 0.25 * k * rng.uniform(0.4, 1))
            ctx.set_line_width(rng.uniform(1, 3))
            ctx.stroke()
        ctx.restore()


def draw_wisps(c, t, J, mode):
    """Spirit wisps around Yone: gathering (mode 'in'), dissolving ('out'), idle."""
    rng = np.random.default_rng(55)
    for i in range(40):
        ph = rng.uniform(0, 1)
        col = hexc('#ff4a5a') if i % 3 == 0 else hexc('#7fc6ff')
        bx = J['hip'][0] + rng.uniform(-60, 60)
        by = J['hip'][1] + rng.uniform(-150, 150)
        if mode == 'in':
            k = seg(t, YONE_IN[0] + ph * 0.6, YONE_IN[0] + ph * 0.6 + 1.0)
            if not (0 < k < 1):
                continue
            ang = rng.uniform(0, TAU)
            d = (1 - e_o(k)) * rng.uniform(120, 260)
            x, y = bx + math.cos(ang) * d, by + math.sin(ang) * d
            a = math.sin(math.pi * k)
        elif mode == 'out':
            k = seg(t, YONE_OUT[0] + ph * 0.8, YONE_OUT[0] + ph * 0.8 + 1.1)
            if not (0 < k < 1):
                continue
            x = bx + 30 * math.sin(k * 6 + i)
            y = by - 260 * e_o(k)
            a = math.sin(math.pi * k)
        else:
            k = (t * 0.5 + ph) % 1
            x = bx + 12 * math.sin(k * 8 + i)
            y = by - 120 * k
            a = 0.35 * math.sin(math.pi * k)
        r = rng.uniform(2, 5)
        c.arc(x, y, r, 0, TAU)
        c.set_source_rgba(*col, a)
        c.fill()


# ------------------------------------------------------------------ fighters
def render_fighter(cam, who, t):
    s, c = new_layer(cam)
    if who == 'yasuo':
        J = solve(YAS(t))
        eye = draw_fighter(c, J, YASUO, chains_for('yasuo', t), drawn_yasuo(t))
    else:
        J = solve(YON(t))
        eye = draw_fighter(c, J, YONE, chains_for('yone', t), drawn_yone(t))
    return s, c, J, eye


def dissolve(surf, t):
    k = seg(t, YONE_OUT[0], YONE_OUT[1])
    if k <= 0:
        return
    surf.flush()
    buf = np.ndarray((H, W, 4), np.uint8, surf.get_data())
    thr = k * 1.25 - 0.1
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    m = np.clip((_NOISE + (1 - ys) * 0.35 - thr) * 6, 0, 1)
    buf[...] = (buf * m[..., None]).astype(np.uint8)
    surf.mark_dirty()


_NOISE = None


def _init_noise():
    global _NOISE
    rng = np.random.default_rng(8)
    n = gaussian_filter(rng.random((H // 6, W // 6)).astype(np.float32), 3)
    n = (n - n.min()) / (n.max() - n.min())
    _NOISE = np.kron(n, np.ones((6, 6), np.float32))[:H, :W]


_init_noise()


# ------------------------------------------------------------------ frame
def render(t):
    cam = camera(t)
    base = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(base)
    ctx.set_matrix(cam)
    draw_sky(ctx, t)
    draw_tree(ctx, t)
    draw_ground(ctx, t)
    draw_grass(ctx, t, (0,))
    draw_petals(ctx, t, False)
    ctx.set_matrix(cam)
    draw_dust(ctx, t)

    # --- Yone (body)
    ya = yone_alpha(t) * (1 - (1 if t >= YONE_OUT[1] else 0))
    sY, cY, JY, eyeY = render_fighter(cam, 'yone', t)
    if SPIRIT_T0 <= t < SPIRIT_T1:
        tint(cY, 0.35 * spirit_alpha(t), hexc('#101830'))
    if t >= YONE_OUT[0]:
        dissolve(sY, t)
    if ya > 0:
        rim_composite(ctx, sY, rim_offset(JY, cam), ya)
    # --- Yasuo
    sA, cA, JA, _ = render_fighter(cam, 'yasuo', t)
    if PASS_T0 <= t < PASS_T1:
        # motion smear: extra ghost copies behind both fighters
        for who, ch, st, dr in (('yasuo', YAS, YASUO, drawn_yasuo), ('yone', YON, YONE, drawn_yone)):
            gs, gc = new_layer(cam)
            for k in range(1, 6):
                tt = t - k * 0.012
                Jg = solve(ch(tt))
                gc.push_group()
                draw_fighter(gc, Jg, st, chains_for(who, tt), dr(tt))
                gc.pop_group_to_source()
                gc.paint_with_alpha(0.35 * (1 - k / 6))
            rim_composite(ctx, gs, (0, 0), 1.0, rim_a=0.0)
    rim_composite(ctx, sA, rim_offset(JA, cam), 1.0)

    # --- FX layer (additive with bloom)
    s, c = new_layer(cam)
    if ya > 0:
        for bl in blade_list('yone', t):
            draw_blade(c, bl[0], bl[1], bl[2], alpha=ya)
        draw_trails(c, 'yone', t, ya)
        if eyeY:
            flare = 1 + 1.5 * math.exp(-abs(t - 2.65) * 8) + 1.5 * math.exp(-abs(t - 12.6) * 8)
            c.move_to(*eyeY[0])
            c.line_to(*eyeY[1])
            c.set_source_rgba(1, 0.25, 0.3, min(1, 0.8 * flare) * ya)
            c.set_line_width(3 + flare)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.stroke()
        if t < YONE_IN[1] + 0.3:
            draw_wisps(c, t, JY, 'in')
        elif t >= YONE_OUT[0]:
            draw_wisps(c, t, JY, 'out')
        else:
            draw_wisps(c, t, JY, 'idle')
    for bl in blade_list('yasuo', t):
        draw_blade(c, bl[0], bl[1], bl[2])
        # blade glint during the standoff
        gk = seg(t, 12.2, 12.7)
        if 0 < gk < 1:
            bb, _tip, d, _n = blade_points(bl[0], bl[1])
            gp = vadd(bb, d, BLADE * gk)
            sparkle_path(c, gp[0], gp[1], 22 * math.sin(math.pi * gk), 0.3)
            c.set_source_rgba(1, 1, 1, 1)
            c.fill()
    draw_trails(c, 'yasuo', t)
    draw_wind_swirls(c, t)
    draw_tornado(c, t)
    draw_xcut(c, t)
    draw_clash_fx(c, t)
    draw_pass_streaks(c, t)
    draw_big_x(c, t)
    draw_spirit_tether(c, t)
    # spirit form
    sa = spirit_alpha(t)
    if sa > 0:
        ss, sc = new_layer(cam)
        for k, (dtk, aa) in enumerate(((0.0, 1.0), (0.035, 0.45), (0.07, 0.25), (0.105, 0.12))):
            tt = t - dtk
            if tt < SPIRIT_T0:
                continue
            Js = solve(SPI(tt))
            sc.push_group()
            draw_fighter(sc, Js, YONE, chains_for('spirit', tt), [True, True])
            sc.pop_group_to_source()
            sc.paint_with_alpha(aa)
        tint(sc, 0.72, hexc('#5aa6ff'))
        ctx.save()
        ctx.identity_matrix()
        ctx.set_source_surface(ss, 0, 0)
        ctx.paint_with_alpha(0.5 * sa)
        ctx.restore()
        c.save()
        c.identity_matrix()
        c.set_source_surface(ss, 0, 0)
        c.paint_with_alpha(0.13 * sa)
        c.restore()
        for bl in blade_list('spirit', t):
            draw_blade(c, bl[0], bl[1], bl[2], alpha=sa)
        draw_trails(c, 'spirit', t, sa)
    bloom_composite(ctx, s, 1.0)

    ctx.set_matrix(cam)
    draw_clash_glows(ctx, t)
    draw_big_x_glow(ctx, t)
    draw_petals(ctx, t, True)
    draw_grass(ctx, t, (1, 2))
    draw_speedlines(ctx, t)

    # grade: vignette + grain
    ctx.identity_matrix()
    g = cairo.RadialGradient(W / 2, H * 0.6, H * 0.25, W / 2, H * 0.6, H * 0.8)
    g.add_color_stop_rgba(0, 0, 0, 0.02, 0)
    g.add_color_stop_rgba(1, 0.02, 0, 0.04, 0.55)
    ctx.set_source(g)
    ctx.paint()
    end = seg(t, 19.4, 20.0)
    if end > 0:
        ctx.set_source_rgba(0.02, 0.0, 0.03, 0.35 * e_io(end))
        ctx.paint()
    GRAIN.set_matrix(cairo.Matrix(x0=(int(t * 30) * 37) % 512, y0=(int(t * 30) * 91) % 512))
    ctx.set_source(GRAIN)
    ctx.paint_with_alpha(0.12)
    base.flush()
    return base

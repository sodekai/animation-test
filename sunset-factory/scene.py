"""Scenery + props drawing and per-frame compositing."""
import math
import numpy as np
import cairo
from core import *
from world import *
from workers import ACTOR_A, ACTOR_B, STYLE_A, STYLE_B, draw_worker, crank_knob

# ------------------------------------------------------------------ palette
SKY_TOP, SKY_BOT = hexc('#D8D2CA'), hexc('#EEE6D6')
PINK_TOP, PINK_BOT, PINK_CLOUD = hexc('#E3628D'), hexc('#F59CA8'), hexc('#F9BDC3')
OR_TOP, OR_MID, OR_BOT, OR_CLOUD = hexc('#F47E4C'), hexc('#F9A457'), hexc('#FCD27D'), hexc('#FDC58C')
PINK_PAINT, OR_PAINT = hexc('#EC7C9C'), hexc('#F79150')
PENCIL = hexc('#5A4E57')


# ------------------------------------------------------------------ sky
def draw_sky_base(c, t):
    g = cairo.LinearGradient(0, 0, 0, 1150)
    g.add_color_stop_rgb(0, *SKY_TOP)
    g.add_color_stop_rgb(1, *SKY_BOT)
    c.rectangle(-300, -300, W + 600, H + 600)
    paper(c, g, seed=3, grain=0.5, rim=0, sh=None, mottle=0.22)
    # pencil guide: "the sun goes here"
    a = 0.5 * (1 - seg(t, 10.9, 11.3))
    if a > 0.01:
        c.save()
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for k, (r, off, aa) in enumerate(((SUNR + 14, 0.0, 1.0), (SUNR + 12, 0.05, 0.5))):
            c.set_source_rgba(*PENCIL, a * aa)
            c.set_line_width(2.4 - k * 0.8)
            c.set_dash([11, 10], off * 40)
            c.arc(SUNX + k, SUNY - k, r, 0, TAU)
            c.stroke()
        c.set_dash([])
        c.set_source_rgba(*PENCIL, a * 0.9)
        c.set_line_width(2.2)
        for dx, dy in ((-9, -9), (9, -9)):
            c.move_to(SUNX + dx, SUNY + dy)
            c.line_to(SUNX - dx, SUNY - dy)
        c.stroke()
        c.restore()


def pink_edge(x):
    return 598 + 20 * math.sin(x * 0.011 + 1.3) + 9 * math.sin(x * 0.029 + 0.4)


def orange_edge(x):
    return 552 + 24 * math.sin(x * 0.0095 + 4.0) + 10 * math.sin(x * 0.027 + 1.7)


def cloud(c, x, y, w, h):
    rrect(c, x - w / 2, y - h * 0.45, w, h * 0.45, h * 0.22)
    bumps = [(-0.28, 0.5), (-0.02, 0.78), (0.26, 0.58)]
    for bx, bh in bumps:
        c.new_sub_path()
        c.arc(x + bx * w, y - h * 0.3, h * bh * 0.62, 0, TAU)


def reveal_clip(c, t, rx, tpass, yr, d, up, dn):
    if d > 0:
        xs = np.arange(-170, rx, 10.0)
    else:
        xs = np.arange(W + 170, rx, -10.0)
    xs = np.append(xs, rx)
    tp = tpass(xs)
    age = t - tp
    k = np.clip(age / 0.4, 0, 1)
    k = 1 - (1 - k) ** 3
    hu = 62 + (up - 62) * k
    hd = 62 + (dn - 62) * k
    wob = 12 * np.sin(xs * 0.045 + 2.5) * (1 - k) + 6 * np.sin(xs * 0.11)
    top = yr - hu + wob
    bot = yr + hd + wob
    c.move_to(xs[0], top[0])
    for x, y in zip(xs[1:], top[1:]):
        c.line_to(x, y)
    c.curve_to(rx + d * 20, yr - 60, rx + d * 20, yr + 60, rx, bot[-1])
    for x, y in zip(xs[::-1], bot[::-1]):
        c.line_to(x, y)
    c.close_path()
    c.clip()


def draw_bands(c, t):
    if t < PT0 - 0.01:
        return False
    full = t > PT1 + 0.8
    # --- pink
    c.save()
    if not full:
        reveal_clip(c, t, pink_rx(t), pink_tpass, PINK_Y, +1, 820, 440)
    c.move_to(-300, -300)
    c.line_to(W + 300, -300)
    wavy_poly(c, pink_edge, W + 300, -300, first=False)
    c.close_path()
    g = cairo.LinearGradient(0, 0, 0, 620)
    g.add_color_stop_rgb(0, *PINK_TOP)
    g.add_color_stop_rgb(1, *PINK_BOT)
    paper(c, g, seed=41, rim=0.25, sh=(2, 4, 0.18), mottle=0.45)
    # roller streaks
    c.set_line_width(2)
    for i in range(-3, 4):
        c.move_to(-50, PINK_Y + i * 17)
        for x in range(0, W + 60, 60):
            c.line_to(x, PINK_Y + i * 17 + 2.5 * math.sin(x * 0.02 + i))
        c.set_source_rgba(1, 1, 1, 0.07 if i % 2 else 0.0)
        c.stroke()
    cloud(c, 215, 205, 250, 70)
    paper(c, PINK_CLOUD, seed=42, rim=0.3, sh=(2, 4, 0.2))
    cloud(c, 850, 395, 210, 58)
    paper(c, PINK_CLOUD, seed=43, rim=0.3, sh=(2, 4, 0.2))
    c.restore()
    # --- orange
    c.save()
    if not full:
        reveal_clip(c, t, orange_rx(t), orange_tpass, ORANGE_Y, -1, 380, 560)
    c.move_to(-300, H)
    wavy_poly(c, orange_edge, -300, W + 300, first=False)
    c.line_to(W + 300, H)
    c.close_path()
    g = cairo.LinearGradient(0, 520, 0, 1080)
    g.add_color_stop_rgb(0, *OR_TOP)
    g.add_color_stop_rgb(0.5, *OR_MID)
    g.add_color_stop_rgb(1, *OR_BOT)
    paper(c, g, seed=51, rim=0.28, sh=(2, 4, 0.18), mottle=0.45)
    c.set_line_width(2)
    for i in range(-3, 4):
        c.move_to(-50, ORANGE_Y + i * 17)
        for x in range(0, W + 60, 60):
            c.line_to(x, ORANGE_Y + i * 17 + 2.5 * math.sin(x * 0.02 + i))
        c.set_source_rgba(1, 1, 1, 0.07 if i % 2 else 0.0)
        c.stroke()
    cloud(c, 215, 745, 220, 60)
    paper(c, OR_CLOUD, seed=52, rim=0.3, sh=(2, 4, 0.2))
    c.restore()
    return True


# ------------------------------------------------------------------ night
NIGHT_A, NIGHT_B, NIGHT_C, NIGHT_D = hexc('#1C1E4C'), hexc('#2B2A63'), hexc('#453878'), hexc('#5E4486')


def night_path(c, t):
    p = seg(t, NIGHT_T0, NIGHT_T1)
    r = 2050 * (0.5 * p + 0.5 * e_s(p))
    cx, cy = JAR_STOP_X - 52, JAR_GROUND_CY
    n = 220
    for k in range(n + 1):
        th = k / n * TAU
        rr = r + (16 + 0.05 * r) * math.sin(7 * th + 1.3 + t * 0.9) + 10 * math.sin(13 * th + 0.4)
        x, y = cx + rr * math.cos(th), cy + rr * math.sin(th)
        if k == 0:
            c.move_to(x, y)
        else:
            c.line_to(x, y)
    c.close_path()
    return p


def draw_night(c, t):
    if t < NIGHT_T0:
        return False
    night_path(c, t)
    g = cairo.LinearGradient(0, 0, 0, 1150)
    g.add_color_stop_rgb(0, *NIGHT_A)
    g.add_color_stop_rgb(0.55, *NIGHT_B)
    g.add_color_stop_rgb(0.85, *NIGHT_C)
    g.add_color_stop_rgb(1, *NIGHT_D)
    path = c.copy_path()
    paper(c, g, seed=61, rim=0.18, sh=(2, 4, 0.25), mottle=0.5)
    c.save()
    c.append_path(path)
    c.clip()
    cloud(c, 250, 470, 230, 52)
    paper(c, hexc('#34336F'), seed=62, rim=0.12, sh=(2, 3, 0.2))
    cloud(c, 830, 250, 190, 46)
    paper(c, hexc('#34336F'), seed=63, rim=0.12, sh=(2, 3, 0.2))
    c.restore()
    return True


# ------------------------------------------------------------------ sun
SUN_C = dict(rim=hexc('#FFB22E'), mid=hexc('#FFC93A'), inner=hexc('#FFDF6E'), core=hexc('#FFF1A8'),
             ray1=hexc('#FFBE35'), ray2=hexc('#FFD95E'))
MOON_C = dict(rim=hexc('#D8CEAE'), mid=hexc('#E8E0C3'), inner=hexc('#F3EDD6'), core=hexc('#FBF8EA'),
              ray1=hexc('#E8E0C3'), ray2=hexc('#F3EDD6'))


def draw_sun(c, S, t):
    m = S['moon']

    def col(k):
        return mixc(SUN_C[k], MOON_C[k], m)
    c.save()
    c.translate(S['x'], S['y'])
    c.scale(S['squash'], 1 / S['squash'])
    k = S['rays'] * (1 - e_io(seg(m, 0.0, 0.55)))
    if k > 0.01:
        rr = t * 0.22
        for i in range(12):
            a = rr + i * TAU / 12
            long_ = i % 2 == 0
            L = (50 if long_ else 32) * k
            hw = (17 if long_ else 13) / (SUNR + 2)
            base = SUNR + 2
            c.move_to(base * math.cos(a - hw), base * math.sin(a - hw))
            c.line_to((base + L) * math.cos(a), (base + L) * math.sin(a))
            c.line_to(base * math.cos(a + hw), base * math.sin(a + hw))
            c.close_path()
            paper(c, col('ray1') if long_ else col('ray2'), seed=70 + i, rim=0.3, sh=(2, 3, 0.2))
    c.arc(0, 0, SUNR, 0, TAU)
    paper(c, col('rim'), seed=80, rim=0.3, sh=(2, 3, 0.2))
    c.arc(0, 0, SUNR - 14, 0, TAU)
    paper(c, col('mid'), seed=81, rim=0.25, sh=(1.5, 2.5, 0.15))
    c.arc(0, 0, SUNR - 36, 0, TAU)
    paper(c, col('inner'), seed=82, rim=0.25, sh=(1.5, 2.5, 0.12))
    # rolling marks
    ma = 0.75 * (1 - m)
    if ma > 0.01:
        c.save()
        c.rotate(S['rot'])
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_width(5)
        c.set_source_rgba(*SUN_C['core'], ma)
        for i in range(6):
            a = i * TAU / 6
            c.arc(0, 0, SUNR - 25, a, a + 0.42)
            c.stroke()
        c.restore()
    c.arc(-SUNR * 0.34, -SUNR * 0.36, 12, 0, TAU)
    c.set_source_rgba(*col('core'), 0.85)
    c.fill()
    # moon craters + crescent shade
    if m > 0.01:
        for (cx, cy, r) in ((-22, 26, 11), (26, -8, 8), (6, 40, 6)):
            c.arc(cx, cy, r, 0, TAU)
            c.set_source_rgba(*MOON_C['rim'], 0.6 * m)
            c.fill()
        c.save()
        c.arc(0, 0, SUNR + 1, 0, TAU)
        c.clip()
        sx = lerp(260, 42, e_io(seg(m, 0.25, 1.0)))
        c.arc(sx, -26, SUNR * 0.97, 0, TAU)
        c.set_source_rgba(*mixc(NIGHT_B, NIGHT_A, 0.3), clamp(m * 1.3))
        c.fill()
        c.restore()
    c.restore()


def draw_sun_glow(ctx, S, t):
    m = S['moon']
    col = mixc((1.0, 0.80, 0.42), (0.72, 0.78, 1.0), m)
    r = lerp(420, 250, m) * (1 + 0.45 * S['flash'])
    a = lerp(0.55, 0.28, m) + 0.35 * S['flash']
    if t < 1.2:
        a *= 0.2 + 0.8 * e_io(seg(t, 0.35, 1.15))
    glow(ctx, S['x'], S['y'], r, col, a)
    glow(ctx, S['x'], S['y'], SUNR * 1.35, (1.0, 0.95, 0.75) if m < 0.5 else (0.95, 0.95, 1.0), 0.25 * (1 - m * 0.5))


# ------------------------------------------------------------------ stars
def draw_star_shape(c, s, x, y, size, rot, alpha=1.0):
    if s['kind'] == 'spark':
        sparkle_path(c, x, y, size * 1.15, rot * 0.3)
    else:
        star_path(c, x, y, size, rot)
    c.set_source_rgba(*SHC, 0.25 * alpha)
    c.save()
    c.translate(1.5, 2.5)
    c.fill_preserve()
    c.restore()
    c.new_path()
    if s['kind'] == 'spark':
        sparkle_path(c, x, y, size * 1.15, rot * 0.3)
    else:
        star_path(c, x, y, size, rot)
    c.set_source_rgba(*s['col'], alpha)
    c.fill_preserve()
    c.set_source_rgba(1, 1, 1, 0.5 * alpha)
    c.set_line_width(1.2)
    c.stroke()


def settled_stars(t):
    out = []
    for s in STARS:
        ta = s['s0'] + s['d']
        if t >= ta:
            k = seg(t, ta, ta + 0.45)
            pop = 1 + 0.55 * math.sin(k * math.pi) * (1 - k)
            tw = 1 + 0.17 * math.sin(TAU * s['tw_f'] * t + s['tw_p'])
            out.append((s, s['E'][0], s['E'][1], s['size'] * pop * tw, s['rot0'] + s['spin'] * s['d'] * 0.3, k, tw))
    return out


def draw_settled_stars(c, t):
    for s, x, y, size, rot, k, tw in settled_stars(t):
        draw_star_shape(c, s, x, y, size, rot)


def draw_settled_glows(ctx, t):
    for s, x, y, size, rot, k, tw in settled_stars(t):
        glow(ctx, x, y, size * 2.8, s['col'], 0.32 * tw)
        if k < 1:
            a = (1 - k)
            sparkle_path(ctx, x, y, size * (1.5 + 2.5 * k), 0.3)
            ctx.set_source_rgba(1, 1, 0.9, 0.7 * a)
            ctx.fill()


def draw_flying_stars(ctx, t):
    for s in STARS:
        if t < s['s0'] or t >= s['s0'] + s['d']:
            continue
        x, y, u = star_pos(s, t)
        # sparkle trail
        for kk in range(1, 8):
            tu = t - kk * 0.026
            if tu < s['s0']:
                break
            px, py, _ = star_pos(s, tu)
            f = 1 - kk / 8
            sparkle_path(ctx, px + 4 * math.sin(kk * 2.1 + s['tw_p']), py, 5.5 * f + 1, kk * 0.7)
            ctx.set_source_rgba(1, 0.97, 0.8, 0.65 * f)
            ctx.fill()
        size = s['size'] * (0.45 + 0.55 * e_o(u * 2.5))
        rot = s['rot0'] + s['spin'] * u * s['d'] * 0.3
        glow(ctx, x, y, size * 3.4, s['col'], 0.55)
        draw_star_shape(ctx, s, x, y, size, rot)


def draw_burst(ctx, t):
    if not (15.0 <= t < 16.4):
        return
    M = jar_mouth(t)
    k = seg(t, 15.02, 16.3)
    a = math.exp(-k * 3.5) * (1 if t >= 15.04 else 0)
    glow(ctx, M[0], M[1], 260 * (0.5 + k), (1.0, 0.95, 0.7), 0.7 * a)
    for i in range(14):
        ang = -math.pi / 2 - 0.9 + i * 0.13 + 0.4 * hash01(i, 3)
        dist = (40 + 260 * hash01(i, 5)) * e_o(k * 1.6)
        px, py = M[0] + dist * math.cos(ang) - 30, M[1] + dist * math.sin(ang)
        sz = (6 + 10 * hash01(i, 7)) * (1 - k)
        if sz > 0.5:
            sparkle_path(ctx, px, py, sz, i)
            ctx.set_source_rgba(1, 1, 0.9, 0.85 * (1 - k))
            ctx.fill()


# ------------------------------------------------------------------ land
BACK_HILL, MID_HILL = hexc('#DD9776'), hexc('#C7735A')
YARD_T, YARD_B, FLOOR = hexc('#B06A51'), hexc('#9A5747'), hexc('#E2B687')


def back_hill_y(x):
    return 1012 + 34 * math.sin(x * 0.0065 + 0.8) + 15 * math.sin(x * 0.018 + 2.1)


def mid_hill_y(x):
    return 1092 + 24 * math.sin(x * 0.0085 + 2.6) + 10 * math.sin(x * 0.022 + 0.3)


def draw_land(c, t):
    c.move_to(-300, 1400)
    wavy_poly(c, back_hill_y, -300, W + 300, first=False)
    c.line_to(W + 300, 1400)
    c.close_path()
    paper(c, BACK_HILL, seed=31, mottle=0.5, rim=0.3)
    for i, tx in enumerate((58, 112, 900, 962, 1028)):
        ty = back_hill_y(tx) + 6
        rrect(c, tx - 3.5, ty - 30, 7, 34, 3)
        paper(c, hexc('#8E4C3E'), seed=90 + i, rim=0.1)
        c.arc(tx, ty - 38, 17 + 4 * hash01(i), 0, TAU)
        paper(c, hexc('#C0654F') if i % 2 else hexc('#B35A48'), seed=95 + i, rim=0.25)
    c.move_to(-300, 1400)
    wavy_poly(c, mid_hill_y, -300, W + 300, first=False)
    c.line_to(W + 300, 1400)
    c.close_path()
    paper(c, MID_HILL, seed=32, mottle=0.5, rim=0.3)
    c.move_to(-300, H + 300)
    wavy_poly(c, lambda x: 1176 + 7 * math.sin(x * 0.012 + 1), -300, W + 300, first=False)
    c.line_to(W + 300, H + 300)
    c.close_path()
    g = cairo.LinearGradient(0, 1170, 0, 1500)
    g.add_color_stop_rgb(0, *YARD_T)
    g.add_color_stop_rgb(1, *YARD_B)
    paper(c, g, seed=33, mottle=0.5, rim=0.3)
    c.move_to(-300, 1600)
    wavy_poly(c, lambda x: 1434 + 5 * math.sin(x * 0.015 + 2), -300, W + 300, first=False)
    wavy_poly(c, lambda x: 1592 + 6 * math.sin(x * 0.013 + 0.5), W + 300, -300, first=False)
    c.close_path()
    paper(c, FLOOR, seed=34, mottle=0.6, rim=0.3)


# ------------------------------------------------------------------ factory + crane
FWALL, FWALL2, TRIM, ROOF = hexc('#EBB86F'), hexc('#E3A65E'), hexc('#8E3F33'), hexc('#7C3F4E')
WIN, LIT = hexc('#5C4B6B'), hexc('#FFD27A')
CHIM, BAND = hexc('#B44C3A'), hexc('#F2DDB0')
CRANE_Y, CRANE_D = hexc('#F2A33A'), hexc('#6B4B57')

WINDOWS = [  # (x, y, w, h, r, light_on_time)
    (96, 1182, 52, 104, 26, 16.45),
    (640, 1198, 50, 50, 6, 16.75),
    (640, 1268, 50, 50, 6, 16.6),
]


def draw_factory(c, t):
    # chimney + smoke
    for i in range(9):
        t0 = -3 + i * 0.62
        age = (t - t0) % (9 * 0.62)
        if age < 0:
            continue
        k = age / 5.2
        if k > 1:
            continue
        x = 357 - 110 * k + 12 * math.sin(age * 1.7 + i)
        y = 872 - 330 * e_o2(k) - 20 * k
        r = 13 + 34 * e_o2(k)
        a = 0.9 * (1 - k) ** 1.2
        c.arc(x, y, r, 0, TAU)
        paper(c, hexc('#F3E7D6', a), seed=110 + i, grain=0.5 * a, rim=0.2 * a, sh=(2, 3, 0.12 * a))
    rrect(c, 330, 885, 56, 240, 3)
    paper(c, CHIM, seed=111, rim=0.25)
    for yy in (905, 930):
        c.rectangle(330, yy, 56, 9)
        paper(c, BAND, seed=112, sh=None, rim=0.1)
    rrect(c, 322, 872, 72, 20, 4)
    paper(c, TRIM, seed=113, rim=0.2)
    c.arc(358, 1000, 18, 0, TAU)
    paper(c, BAND, seed=114, rim=0.2)
    c.arc(358, 1006, 9, math.pi, TAU)
    c.close_path()
    c.set_source_rgb(*hexc('#F08A3C'))
    c.fill()
    for i in range(5):
        a = math.pi + (i + 0.5) * math.pi / 5
        c.move_to(358 + 11 * math.cos(a), 1006 + 11 * math.sin(a))
        c.line_to(358 + 15 * math.cos(a), 1006 + 15 * math.sin(a))
    c.set_line_width(2)
    c.stroke()

    # left block
    c.rectangle(80, 1110, 372, 262)
    paper(c, FWALL, seed=120, mottle=0.4, rim=0.3)
    for i in range(3):
        x0 = 80 + i * 124
        c.move_to(x0, 1113)
        c.line_to(x0 + 124, 1050)
        c.line_to(x0 + 124, 1113)
        c.close_path()
        paper(c, ROOF, seed=121 + i, rim=0.25)
        rrect(c, x0 + 124 - 18, 1062, 12, 44, 3)
        paper(c, WIN, seed=125 + i, sh=None, rim=0.15)
    c.rectangle(74, 1106, 384, 10)
    paper(c, TRIM, seed=128, rim=0.2)
    # brick hints
    c.set_source_rgba(*TRIM, 0.13)
    c.set_line_width(2)
    for (bx, by) in ((390, 1150), (412, 1172), (395, 1300), (110, 1320), (125, 1340), (420, 1330)):
        c.rectangle(bx, by, 26, 10)
        c.stroke()
    # door
    rrect(c, 158, 1160, 224, 226, 32)
    paper(c, TRIM, seed=129, rim=0.25)
    rrect(c, 170, 1172, 200, 214, 24)
    ins = cairo.RadialGradient(270, 1300, 10, 270, 1300, 190)
    glowk = 1 - seg(t, 1.6, 3.0)
    ins.add_color_stop_rgb(0, *mixc(hexc('#3A2430'), hexc('#8A4A36'), glowk))
    ins.add_color_stop_rgb(1, *hexc('#2A1A24'))
    paper(c, ins, seed=130, rim=0.1, sh=None)
    # interior: a pipe and a spare-sun rack silhouette
    c.save()
    rrect(c, 170, 1172, 200, 214, 24)
    c.clip()
    c.set_source_rgba(0.1, 0.05, 0.08, 0.45)
    c.rectangle(190, 1198, 160, 7)
    c.fill()
    for i in range(3):
        c.arc(215 + i * 55, 1188, 16, math.pi, TAU)
        c.fill()
    c.restore()
    # tall window + porthole
    x, y, w, h, r, _ = WINDOWS[0]
    rrect(c, x - 5, y - 5, w + 10, h + 10, r + 5)
    paper(c, TRIM, seed=131, rim=0.2)
    rrect(c, x, y, w, h, r)
    paper(c, WIN, seed=132, sh=None, rim=0.15)
    c.arc(417, 1238, 20, 0, TAU)
    paper(c, TRIM, seed=133, rim=0.2)
    c.arc(417, 1238, 14, 0, TAU)
    paper(c, WIN, seed=134, sh=None, rim=0.15)

    # right block
    c.rectangle(452, 1175, 256, 197)
    paper(c, FWALL2, seed=140, mottle=0.4, rim=0.3)
    rrect(c, 442, 1160, 276, 18, 4)
    paper(c, ROOF, seed=141, rim=0.25)
    # gears
    rot = t * 0.9
    gear_path(c, 527, 1278, 46, 10, rot)
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    paper(c, hexc('#F0A23A'), seed=142, rim=0.3, sh=(2.5, 3.5, 0.25))
    gear_path(c, 602, 1233, 29, 7, -rot * 46 / 29 + 0.2)
    paper(c, hexc('#D9763A'), seed=143, rim=0.3, sh=(2.5, 3.5, 0.25))
    c.set_fill_rule(cairo.FILL_RULE_WINDING)
    for (gx, gy) in ((527, 1278), (602, 1233)):
        c.arc(gx, gy, 5, 0, TAU)
        c.set_source_rgb(*TRIM)
        c.fill()
    for (x, y, w, h, r, _) in WINDOWS[1:]:
        rrect(c, x - 5, y - 5, w + 10, h + 10, r + 3)
        paper(c, TRIM, seed=150 + y, rim=0.2)
        rrect(c, x, y, w, h, r)
        paper(c, WIN, seed=151 + y, sh=None, rim=0.15)
    # wall lamp
    rrect(c, 452, 1190, 22, 6, 2)
    paper(c, TRIM, seed=160, rim=0.1)
    c.arc(474, 1206, 13, math.pi, TAU)
    c.close_path()
    paper(c, hexc('#5E4A57'), seed=161, rim=0.2)
    c.rectangle(70, 1362, 646, 16)
    paper(c, hexc('#7A4A45'), seed=162, rim=0.15)

    draw_crane(c, t)


def draw_factory_emissive(ctx_layer, t, night):
    """Lit windows + lamp bulb drawn onto the (already tinted) factory layer."""
    c = ctx_layer
    for i, (x, y, w, h, r, ton) in enumerate(WINDOWS):
        k = seg(t, ton, ton + 0.25)
        if k <= 0:
            continue
        flick = 1.0 if k >= 1 else (0.5 + 0.5 * math.sin(k * 40)) * k
        rrect(c, x, y, w, h, r)
        c.set_source_rgba(*LIT, flick)
        c.fill()
        c.set_source_rgba(*TRIM, 0.5 * flick)
        c.set_line_width(3)
        c.move_to(x + w / 2, y + 4)
        c.line_to(x + w / 2, y + h - 4)
        c.move_to(x + 4, y + h / 2)
        c.line_to(x + w - 4, y + h / 2)
        c.stroke()
    for i in range(3):
        k = seg(t, 16.9 + i * 0.12, 17.1 + i * 0.12)
        if k > 0:
            x0 = 80 + i * 124
            rrect(c, x0 + 124 - 18, 1062, 12, 44, 3)
            c.set_source_rgba(*LIT, k)
            c.fill()
    lk = lamp_on(t)
    if lk > 0:
        c.arc(474, 1208, 8, 0, math.pi)
        c.set_source_rgba(1, 0.93, 0.7, lk)
        c.fill()


def lamp_on(t):
    k = seg(t, 16.6, 16.8)
    if k <= 0:
        return 0.0
    if k >= 1:
        return 1.0
    return (0.6 + 0.4 * math.sin(k * 55)) * k


def factory_glows(ctx, t):
    for i, (x, y, w, h, r, ton) in enumerate(WINDOWS):
        k = seg(t, ton, ton + 0.25)
        if k > 0:
            glow(ctx, x + w / 2, y + h / 2, 110, (1.0, 0.78, 0.4), 0.35 * k)
    lk = lamp_on(t)
    if lk > 0:
        glow(ctx, 474, 1215, 470, (1.0, 0.76, 0.42), 0.33 * lk)
        glow(ctx, 474, 1210, 60, (1.0, 0.9, 0.7), 0.6 * lk)


def draw_crane(c, t):
    cs = crane_state(t)
    P = CRANE_P
    tip = cs['tip']
    L = math.hypot(tip[0] - P[0], tip[1] - P[1])
    ang = math.atan2(tip[1] - P[1], tip[0] - P[0])
    # cab
    rrect(c, 640, 1112, 36, 44, 5)
    paper(c, CRANE_D, seed=170, rim=0.2)
    rrect(c, 546, 1098, 98, 64, 11)
    paper(c, CRANE_Y, seed=171, rim=0.3)
    rrect(c, 558, 1106, 56, 32, 7)
    paper(c, hexc('#A9D5DE'), seed=172, sh=None, rim=0.2)
    # operator
    look = 0.0
    s = sun_state(t)
    dx = s['x'] - 586
    look = clamp(dx / 200, -1, 1)
    c.save()
    rrect(c, 558, 1106, 56, 32, 7)
    c.clip()
    c.arc(586, 1130, 12, 0, TAU)
    paper(c, hexc('#E8AE88'), seed=173, sh=None, rim=0.1)
    c.arc(586 + look * 1.5, 1124, 13, math.pi, TAU)
    c.close_path()
    paper(c, hexc('#4F7FB5'), seed=174, sh=None, rim=0.15)
    happy = 11.0 <= t < 13.9
    for sd in (-1, 1):
        ex, ey = 586 + sd * 5 + look * 3, 1130
        if happy:
            c.arc(ex, ey + 1.5, 2.6, math.pi + 0.3, TAU - 0.3)
            c.set_source_rgb(0.16, 0.12, 0.15)
            c.set_line_width(1.6)
            c.stroke()
        else:
            c.arc(ex, ey, 1.9, 0, TAU)
            c.set_source_rgb(0.16, 0.12, 0.15)
            c.fill()
    c.restore()
    rrect(c, 540, 1156, 114, 9, 3)
    paper(c, CRANE_D, seed=175, rim=0.15)
    # telescoping boom
    ln = 205.0
    e = max(0.0, L - ln)
    widths = [26, 21, 17, 13]
    cols = [CRANE_Y, shade(CRANE_Y, 0.95), shade(CRANE_Y, 0.9), shade(CRANE_Y, 0.86)]
    c.save()
    c.translate(*P)
    c.rotate(ang)
    for i in (3, 2, 1, 0):
        st = i * e / 3
        w = widths[i]
        x0 = st - (10 if i == 0 else 0)
        x1 = st + ln
        rrect(c, x0, -w / 2, x1 - x0, w, w * 0.3)
        paper(c, cols[i], seed=180 + i, rim=0.25, sh=(2, 3, 0.25))
        # truss zig-zag
        c.set_source_rgba(*CRANE_D, 0.55)
        c.set_line_width(2.2)
        yy = w / 2 - 3.5
        x = x0 + 8
        c.move_to(x, -yy)
        up = True
        while x < x1 - 14:
            x += 15
            c.line_to(x, yy if up else -yy)
            up = not up
        c.stroke()
    c.arc(L, 0, 9, 0, TAU)
    paper(c, CRANE_D, seed=185, rim=0.2)
    c.arc(L, 0, 3, 0, TAU)
    c.set_source_rgb(*CRANE_Y)
    c.fill()
    c.restore()
    c.arc(P[0], P[1], 9, 0, TAU)
    paper(c, CRANE_D, seed=186, rim=0.2)


def draw_cable_claw(c, t):
    cs = crane_state(t)
    tip, L, phi, o = cs['tip'], cs['cable'], cs['phi'], cs['claw']
    hx, hy = tip[0] + L * math.sin(phi), tip[1] + L * math.cos(phi)
    c.move_to(*tip)
    c.line_to(hx, hy)
    pstroke(c, hexc('#3A2C35'), 3, sh=(2, 3, 0.25))
    c.save()
    c.translate(hx, hy)
    c.rotate(-phi)
    for sd in (-1, 1):
        tx, ty = sd * lerp(52, 72, o), lerp(44, 18, o)
        c.move_to(sd * 8, 8)
        c.curve_to(sd * 38, 6, sd * (58 + 14 * o), lerp(22, 6, o), tx, ty)
        pstroke(c, hexc('#5B4753'), 7, sh=(2, 3, 0.25))
        c.arc(tx, ty, 4.5, 0, TAU)
        c.set_source_rgb(*hexc('#5B4753'))
        c.fill()
    rrect(c, -14, -8, 28, 20, 5)
    paper(c, hexc('#5B4753'), seed=190, rim=0.2)
    c.rectangle(-14, -1, 28, 5)
    c.set_source_rgb(*CRANE_Y)
    c.fill()
    c.restore()


# ------------------------------------------------------------------ conveyor
def draw_conveyor(c, t):
    off = belt_offset(t)
    for i, lx in enumerate((205, 492, 780)):
        c.rectangle(lx - 7, 1408, 14, 60)
        paper(c, hexc('#5E4752'), seed=200 + i, rim=0.15)
        rrect(c, lx - 18, 1463, 36, 8, 3)
        paper(c, hexc('#4C3843'), seed=203 + i, rim=0.1)
    c.move_to(212, 1418)
    c.line_to(485, 1458)
    c.move_to(499, 1418)
    c.line_to(773, 1458)
    pstroke(c, hexc('#5E4752'), 4, sh=(1, 2, 0.2))
    rrect(c, 150, 1378, 686, 38, 19)
    paper(c, hexc('#3C2F37'), seed=206, rim=0.2)
    rrect(c, 172, 1387, 642, 20, 6)
    paper(c, hexc('#7A5A6C'), seed=207, sh=None, rim=0.15)
    for i, x in enumerate(range(196, 810, 56)):
        c.arc(x, 1397, 8, 0, TAU)
        paper(c, hexc('#D6AA7C'), seed=210 + i, sh=(1, 1.5, 0.2), rim=0.15)
        a = off / 8 + i
        c.move_to(x - 6 * math.cos(a), 1397 - 6 * math.sin(a))
        c.line_to(x + 6 * math.cos(a), 1397 + 6 * math.sin(a))
        c.set_source_rgb(*hexc('#8A6650'))
        c.set_line_width(2)
        c.stroke()
    # treads on top of belt
    c.save()
    c.rectangle(166, 1376, 654, 10)
    c.clip()
    c.set_source_rgba(1, 0.95, 0.9, 0.22)
    c.set_line_width(3)
    for k in range(26):
        x = 150 + ((k * 28 + off) % 700)
        c.move_to(x, 1379)
        c.line_to(x + 5, 1384)
    c.stroke()
    c.restore()
    for x in (169, 817):
        c.arc(x, 1397, 16, 0, TAU)
        paper(c, hexc('#8C6F7C'), seed=230 + x, rim=0.2)
        c.arc(x, 1397, 4, 0, TAU)
        c.set_source_rgb(*hexc('#3C2F37'))
        c.fill()
    # bumper
    rrect(c, 836, 1328, 17, 66, 6)
    paper(c, hexc('#D65A3C'), seed=240, rim=0.25)
    c.arc(844, 1340, 3, 0, TAU)
    c.set_source_rgb(*hexc('#8E3F33'))
    c.fill()
    # crank
    kx, ky = crank_knob(t)
    c.move_to(*CRANK_C)
    c.line_to(kx, ky)
    pstroke(c, hexc('#9C7C6C'), 7, sh=(1.5, 2.5, 0.25))
    c.arc(kx, ky, 6.5, 0, TAU)
    paper(c, hexc('#D65A3C'), seed=241, rim=0.2)


def draw_shutter(c, t):
    o = e_io(seg(t, 0.35, 1.15))
    h = 214 * (1 - o)
    if h > 1:
        c.save()
        rrect(c, 170, 1172, 200, 214, 24)
        c.clip()
        c.rectangle(170, 1172, 200, h)
        paper(c, hexc('#C98B61'), seed=250, sh=None, rim=0.15)
        c.set_source_rgba(*hexc('#8E5A40'), 0.55)
        c.set_line_width(2.5)
        y = 1172 + h - 14
        while y > 1172:
            c.move_to(170, y)
            c.line_to(370, y)
            y -= 15
        c.stroke()
        c.rectangle(170, 1172 + h - 8, 200, 8)
        c.set_source_rgb(*hexc('#6E4636'))
        c.fill()
        c.restore()
    rrect(c, 160, 1156, 220, 20, 10)
    paper(c, hexc('#A86F4E'), seed=251, rim=0.25, sh=(2, 3, 0.25))


# ------------------------------------------------------------------ buckets, poles, crate, jar
def draw_bucket_back(c, x, col):
    c.arc(x, BUCKET_BOTTOM - 50, 27, math.pi, TAU)
    c.set_source_rgb(*hexc('#7E7A77'))
    c.set_line_width(2.5)
    c.stroke()


def draw_bucket(c, x, col, seed):
    b = BUCKET_BOTTOM
    c.save()
    c.translate(x, b + 2)
    c.scale(1, 0.22)
    c.arc(0, 0, 32, 0, TAU)
    c.restore()
    c.set_source_rgba(*SHC, 0.25)
    c.fill()
    c.move_to(x - 26, b - 50)
    c.line_to(x + 26, b - 50)
    c.line_to(x + 21, b)
    c.line_to(x - 21, b)
    c.close_path()
    paper(c, hexc('#B9B2AA'), seed=seed, rim=0.3)
    c.rectangle(x - 24, b - 36, 48, 16)
    paper(c, col, seed=seed + 1, sh=None, rim=0.15)
    rrect(c, x - 29, b - 55, 58, 9, 4)
    paper(c, hexc('#8F8984'), seed=seed + 2, rim=0.2)
    for dx, ln in ((-14, 14), (6, 20), (18, 10)):
        rrect(c, x + dx - 3.5, b - 50, 7, ln, 3.5)
        c.set_source_rgb(*col)
        c.fill()


def draw_pole(c, ps, col, seed):
    E, Bt, Rc, d, p = pole_points(ps)
    Lt = ps['La'] + ps['Lb']
    # telescoping segments from the handle end
    segs = [(0, min(Lt, 150), 8), (min(Lt, 140), min(Lt, 150 + (Lt - 150) * 0.5), 6.2), (150 + (Lt - 150) * 0.5 - 8, Lt, 5)]
    for i, (s0, s1, w) in enumerate(segs):
        if s1 <= s0:
            continue
        c.move_to(Bt[0] + d[0] * s0, Bt[1] + d[1] * s0)
        c.line_to(Bt[0] + d[0] * s1, Bt[1] + d[1] * s1)
        pstroke(c, [hexc('#8C6A58'), hexc('#A7836C'), hexc('#BFA088')][i], w, sh=(1.5, 2.5, 0.22),
                cap=cairo.LINE_CAP_BUTT if i else cairo.LINE_CAP_ROUND)
    # grip end
    c.move_to(Bt[0], Bt[1])
    c.line_to(Bt[0] + d[0] * 30, Bt[1] + d[1] * 30)
    pstroke(c, hexc('#5A3E3A'), 10, sh=None)
    # yoke
    Y1 = (E[0] + d[0] * 18, E[1] + d[1] * 18)
    Y2 = (Y1[0] + p[0] * 24, Y1[1] + p[1] * 24)
    c.move_to(*E)
    c.line_to(*Y1)
    c.line_to(*Y2)
    pstroke(c, hexc('#8F8984'), 3.5, sh=(1, 2, 0.2))
    # roller
    phi = ps['phi']
    c.save()
    c.translate(*Rc)
    c.rotate(phi)
    rrect(c, -16, -48, 32, 96, 13)
    paper(c, col, seed=seed, rim=0.35, sh=(2, 3, 0.25))
    for yy in (-48, 40):
        rrect(c, -16, yy, 32, 8, 3)
        c.set_source_rgba(*shade(col, 0.8), 1)
        c.fill()
    c.set_source_rgba(1, 1, 1, 0.25)
    rrect(c, -9, -40, 6, 74, 3)
    c.fill()
    c.restore()


def draw_drips(c, t, who, col):
    if not (PT0 < t < PT1 + 0.9):
        return
    for k in range(9):
        ts = PT0 + 0.08 + k * 0.2 + 0.07 * hash01(k, 11 if who == 'A' else 13)
        if not (ts <= t < ts + 0.8) or ts > PT1:
            continue
        ps = pole_state(ts, who)
        E, Bt, Rc, d, p = pole_points(ps)
        x0 = Rc[0] - d[0] * 50
        y0 = Rc[1] - d[1] * 50
        a = t - ts
        y = y0 + 0.5 * 1500 * a * a
        x = x0 + 10 * a * (1 if who == 'B' else -1)
        stretch = 1 + min(1.2, a * 3)
        c.save()
        c.translate(x, y)
        c.scale(1 / math.sqrt(stretch), stretch)
        c.move_to(0, -7)
        c.curve_to(4, -2, 6, 2, 6, 4)
        c.arc(0, 4, 6, 0, math.pi)
        c.curve_to(-6, 2, -4, -2, 0, -7)
        c.restore()
        c.set_source_rgba(*col, 1 - a / 0.8)
        c.fill()


def draw_crate(c, t):
    x = CRATE_X + CRATE_DX(t)
    y, w, h = CRATE_Y, CRATE_W, CRATE_H
    c.save()
    c.translate(x + w / 2, y + h + 2)
    c.scale(1, 0.18)
    c.arc(0, 0, 66, 0, TAU)
    c.restore()
    c.set_source_rgba(*SHC, 0.28)
    c.fill()
    rrect(c, x, y, w, h, 5)
    paper(c, hexc('#A9744A'), seed=260, rim=0.25)
    for i in range(3):
        rrect(c, x + 5, y + 5 + i * 32.5, w - 10, 29, 3)
        paper(c, hexc('#D29E6A'), seed=261 + i, sh=(1, 1.5, 0.18), rim=0.2)
    c.move_to(x + 10, y + h - 10)
    c.line_to(x + w - 10, y + 10)
    pstroke(c, hexc('#B37D4E'), 10, sh=(1.5, 2, 0.2), cap=cairo.LINE_CAP_SQUARE)
    for (nx, ny) in ((x + 9, y + 9), (x + w - 9, y + 9), (x + 9, y + h - 9), (x + w - 9, y + h - 9)):
        c.arc(nx, ny, 2.4, 0, TAU)
        c.set_source_rgb(*hexc('#5A3E3A'))
        c.fill()


JAR_INNER = [(-18, -26, 7), (10, -28, 6), (22, -14, 5), (-24, -10, 5), (-2, -16, 6), (-16, 34, 6), (14, 36, 7),
             (26, 28, 5), (0, 40, 5)]


def draw_jar(c, t):
    js = jar_state(t)
    popped = js['popped']
    c.save()
    c.translate(*js['c'])
    c.rotate(-js['psi'])
    # glass
    rrect(c, -35, -36, 70, 82, 17)
    rrect(c, -26, -46, 52, 14, 5)
    c.set_source_rgba(*SHC, 0.22)
    c.save()
    c.translate(2, 3)
    c.fill_preserve()
    c.restore()
    c.new_path()
    rrect(c, -35, -36, 70, 82, 17)
    rrect(c, -26, -46, 52, 14, 5)
    c.set_source_rgba(0.83, 0.92, 0.95, 0.62)
    c.fill()
    if not popped:
        for i, (sx, sy, r) in enumerate(JAR_INNER):
            jig = 1.5 * math.sin(t * 3 + i * 1.7)
            star_path(c, sx + jig, sy - jig * 0.5, r + 1.2, t * 0.6 + i)
            c.set_source_rgb(*hexc('#FFD95E'))
            c.fill()
    else:
        for i in range(3):
            k = seg(t, 15.05, 16.2)
            sparkle_path(c, -12 + i * 14, -5 + 12 * math.sin(i * 2 + t * 4), 5 * (1 - k) + 1, t)
            c.set_source_rgba(1, 1, 0.85, 0.8 * (1 - k))
            c.fill()
    # label
    rrect(c, -22, -4, 44, 26, 4)
    paper(c, hexc('#F6ECD2'), seed=270, sh=(1, 1.5, 0.15), rim=0.1)
    star_path(c, 0, 9, 8.5, 0)
    c.set_source_rgb(*hexc('#E8913A'))
    c.fill()
    # highlights + glass edge
    rrect(c, -28, -28, 7, 64, 3.5)
    c.set_source_rgba(1, 1, 1, 0.55)
    c.fill()
    rrect(c, -35, -36, 70, 82, 17)
    rrect(c, -26, -46, 52, 14, 5)
    c.set_source_rgba(1, 1, 1, 0.75)
    c.set_line_width(2.4)
    c.stroke()
    if not popped:
        rrect(c, -22, -60, 44, 17, 4)
        paper(c, hexc('#B98556'), seed=271, rim=0.2, sh=(1.5, 2, 0.2))
    c.restore()


def cork_state(t):
    if t < 15.05:
        return None
    M = jar_mouth(15.05)
    a = t - 15.05
    T = 0.62
    a2 = min(a, T)
    x = M[0] - 330 * a2
    y = M[1] - 620 * a2 + 1100 * a2 * a2
    rot = 13 * a2
    if a > T:
        k = seg(a, T, T + 0.3)
        y -= 12 * math.sin(math.pi * k)
        x -= 25 * e_o(k)
        rot += 2 * e_o(k)
    return (x, y, rot)


def draw_cork(c, t):
    cs = cork_state(t)
    if cs is None:
        return
    x, y, rot = cs
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    rrect(c, -22, -8.5, 44, 17, 4)
    paper(c, hexc('#B98556'), seed=271, rim=0.2, sh=(1.5, 2, 0.25))
    c.restore()


def draw_bang(c, x, y, t0, t):
    k = seg(t, t0, t0 + 0.22)
    fade = 1 - seg(t, t0 + 0.6, t0 + 0.8)
    if k <= 0 or fade <= 0:
        return
    s = e_back(k, 3.0)
    c.save()
    c.translate(x, y)
    c.rotate(0.14)
    c.scale(s, s)
    for pass_ in (0, 1):
        rrect(c, -8, -40, 16, 38, 8)
        c.new_sub_path()
        c.arc(0, 12, 8.5, 0, TAU)
        if pass_ == 0:
            c.set_source_rgba(1, 0.97, 0.9, fade)
            c.set_line_width(8)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke()
        else:
            paper(c, hexc('#E4553F', fade), seed=280, rim=0.2, sh=(2, 3, 0.25 * fade))
    c.restore()


def draw_heart(c, x, y, t0, t, col):
    k = seg(t, t0, t0 + 1.25)
    if k <= 0 or k >= 1:
        return
    s = 16 * e_back(seg(t, t0, t0 + 0.25), 2.5) * (1 - 0.25 * k)
    a = 1 - seg(k, 0.7, 1.0)
    y -= 80 * e_o2(k)
    x += 7 * math.sin(k * 7)
    c.move_to(x, y + s * 0.9)
    c.curve_to(x - s * 1.4, y + s * 0.05, x - s * 0.85, y - s * 1.0, x, y - s * 0.32)
    c.curve_to(x + s * 0.85, y - s * 1.0, x + s * 1.4, y + s * 0.05, x, y + s * 0.9)
    c.close_path()
    paper(c, col + (a,), seed=295, grain=0.5 * a, rim=0.35 * a, sh=(1.5, 2.5, 0.25 * a))


def draw_sweat(c, x, y, t0, t):
    k = seg(t, t0, t0 + 0.3)
    if k <= 0:
        return
    dy = 10 * e_io(seg(t, t0 + 0.3, t0 + 1.2))
    c.save()
    c.translate(x, y + dy)
    c.scale(e_back(k), e_back(k))
    c.move_to(0, -11)
    c.curve_to(3, -5, 7, -1, 7, 3)
    c.arc(0, 3, 7, 0, math.pi)
    c.curve_to(-7, -1, -3, -5, 0, -11)
    c.close_path()
    paper(c, hexc('#A9DDF0'), seed=290, rim=0.4, sh=(1.5, 2, 0.2))
    c.restore()


# ------------------------------------------------------------------ foreground
def fg_y(x):
    return 1600 + 9 * math.sin(x * 0.018 + 0.7) + 5 * math.sin(x * 0.047 + 2.0)


def draw_foreground(c, t):
    c.move_to(-300, H + 300)
    wavy_poly(c, fg_y, -300, W + 300, first=False)
    c.line_to(W + 300, H + 300)
    c.close_path()
    g = cairo.LinearGradient(0, 1600, 0, 1920)
    g.add_color_stop_rgb(0, *hexc('#94503F'))
    g.add_color_stop_rgb(1, *hexc('#7A3F36'))
    paper(c, g, seed=300, mottle=0.6, rim=0.3)
    c.move_to(-300, H + 300)
    wavy_poly(c, lambda x: 1745 + 14 * math.sin(x * 0.011 + 2.2), -300, W + 300, first=False)
    c.line_to(W + 300, H + 300)
    c.close_path()
    paper(c, hexc('#733A33'), seed=301, mottle=0.5, rim=0.25)
    # grass tufts
    for i in range(16):
        x = 20 + i * 68 + 20 * hash01(i, 1)
        y = fg_y(x) + 4
        col = hexc('#6E3833') if i % 2 else hexc('#A35F48')
        sway = 0.08 * math.sin(t * 1.5 + i)
        for j in range(3):
            a = -math.pi / 2 + (j - 1) * 0.45 + sway
            ln = 22 + 10 * hash01(i, j + 3)
            c.move_to(x - 5 + j * 5, y)
            c.line_to(x + j * 5 + ln * math.cos(a), y + ln * math.sin(a))
            c.line_to(x + 5 + j * 5, y)
            c.close_path()
        paper(c, col, seed=310 + i, rim=0.2, sh=(1.5, 2, 0.2))
    # paper flowers
    for i, (x, y) in enumerate(((70, 1650), (190, 1690), (930, 1660), (1010, 1700), (560, 1680), (360, 1665))):
        sway = 0.06 * math.sin(t * 1.3 + i * 2)
        c.save()
        c.translate(x, y)
        c.rotate(sway)
        for k in range(5):
            a = k * TAU / 5 + i
            c.arc(10 * math.cos(a), 10 * math.sin(a), 8, 0, TAU)
            c.new_sub_path()
        paper(c, hexc('#F6E3C0') if i % 2 else hexc('#F7B8A8'), seed=320 + i, rim=0.2, sh=(1.5, 2, 0.22))
        c.arc(0, 0, 6, 0, TAU)
        paper(c, hexc('#F2A93B'), seed=330 + i, sh=None, rim=0.15)
        c.restore()


# ------------------------------------------------------------------ post
def vignette(ctx):
    g = cairo.RadialGradient(W / 2, H * 0.48, H * 0.3, W / 2, H * 0.48, H * 0.78)
    g.add_color_stop_rgba(0, 0.25, 0.1, 0.1, 0)
    g.add_color_stop_rgba(1, 0.25, 0.1, 0.1, 0.32)
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source(g)
    ctx.paint()
    ctx.restore()


# ------------------------------------------------------------------ frame
def render(t):
    cam = camera(t)
    night = night_amount(t)
    base = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(base)
    ctx.set_matrix(cam)
    draw_sky_base(ctx, t)

    s, c = new_layer(cam)
    if draw_bands(c, t):
        composite(ctx, s, sh=(2, 7, 1.6, 0.32))
    s, c = new_layer(cam)
    if draw_night(c, t):
        composite(ctx, s, sh=(2, 7, 1.6, 0.38))

    S = sun_state(t)
    s, c = new_layer(cam)
    draw_settled_stars(c, t)
    composite(ctx, s, sh=(3, 8, 1.8, 0.28))
    ctx.set_matrix(cam)
    draw_settled_glows(ctx, t)

    s, c = new_layer(cam)
    draw_land(c, t)
    tint(c, 0.5 * night)
    composite(ctx, s, sh=(0, 8, 2.2, 0.3))

    s, c = new_layer(cam)
    draw_factory(c, t)
    tint(c, 0.45 * night)
    draw_factory_emissive(c, t, night)
    composite(ctx, s, sh=(5, 9, 1.8, 0.38))

    ctx.set_matrix(cam)
    draw_sun_glow(ctx, S, t)
    factory_glows(ctx, t)
    if not S['front']:
        s, c = new_layer(cam)
        draw_sun(c, S, t)
        composite(ctx, s, sh=(5, 9, 1.8, 0.36))

    s, c = new_layer(cam)
    draw_conveyor(c, t)
    if S['front']:
        draw_sun(c, S, t)
    draw_cable_claw(c, t)
    draw_shutter(c, t)
    tint(c, 0.45 * night)
    composite(ctx, s, sh=(5, 9, 1.8, 0.36))

    # buckets, poles, workers
    s, c = new_layer(cam)
    psA, psB = pole_state(t, 'A'), pole_state(t, 'B')
    heldA = 5.55 <= t < 8.78
    heldB = 5.5 <= t < 8.78
    for x, col in ((PINK_BUCKET_X, PINK_PAINT), (ORANGE_BUCKET_X, OR_PAINT)):
        draw_bucket_back(c, x, col)
    if not heldB:
        draw_pole(c, psB, PINK_PAINT, 400)
    if not heldA:
        draw_pole(c, psA, OR_PAINT, 401)
    draw_bucket(c, PINK_BUCKET_X, PINK_PAINT, 410)
    draw_bucket(c, ORANGE_BUCKET_X, OR_PAINT, 420)
    draw_drips(c, t, 'A', OR_PAINT)
    draw_drips(c, t, 'B', PINK_PAINT)
    PA, PB = ACTOR_A.pose(t), ACTOR_B.pose(t)
    if heldA:
        draw_pole(c, psA, OR_PAINT, 401)
    draw_worker(c, STYLE_A, PA, t)
    if heldB:
        draw_pole(c, psB, PINK_PAINT, 400)
    draw_worker(c, STYLE_B, PB, t)
    tint(c, 0.3 * night)
    composite(ctx, s, sh=(5, 9, 1.6, 0.36))

    # front props
    s, c = new_layer(cam)
    draw_crate(c, t)
    draw_jar(c, t)
    draw_cork(c, t)
    tint(c, 0.35 * night)
    draw_bang(c, PB['x'] + 44, ROW_B - 236, 14.02, t)
    draw_sweat(c, PB['x'] + 40, ROW_B - 198, 18.6, t)
    for (who, t0, dx, col) in (('A', 11.62, -14, hexc('#E4553F')), ('B', 11.8, 16, hexc('#F07C98')),
                               ('A', 12.35, 20, hexc('#F07C98')), ('B', 12.75, -10, hexc('#E4553F'))):
        P = PA if who == 'A' else PB
        row = ROW_A if who == 'A' else ROW_B
        draw_heart(c, P['x'] + dx, row - 222, t0, t, col)
    composite(ctx, s, sh=(5, 9, 1.6, 0.36))

    ctx.set_matrix(cam)
    js = jar_state(t)
    if not js['popped']:
        glow(ctx, js['c'][0], js['c'][1], 95, (1.0, 0.9, 0.55), 0.28 + 0.06 * math.sin(t * 3))
    draw_burst(ctx, t)
    draw_flying_stars(ctx, t)

    s, c = new_layer(cam)
    draw_foreground(c, t)
    tint(c, 0.55 * night)
    composite(ctx, s, sh=(0, -6, 2.0, 0.3))

    vignette(ctx)
    ctx.identity_matrix()
    GRAIN.set_matrix(cairo.Matrix(x0=13, y0=29))
    ctx.set_source(GRAIN)
    ctx.paint_with_alpha(0.2)
    base.flush()
    return base

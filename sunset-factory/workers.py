"""Paper-doll workers: rig, IK arms, expressions and choreography."""
import math
import cairo
from core import *
from world import *

CS = CHAR_S

L1, L2 = 30.0, 28.0

STYLE_A = dict(over=hexc('#3E7F8E'), over_d=hexc('#2D6572'), shirt=hexc('#F4E4C4'), hat=hexc('#FFC83D'),
               hat_l=hexc('#FFE08A'), skin=hexc('#F2C29E'), skin_d=hexc('#DC9E7A'), boot=hexc('#5A3A38'),
               button=hexc('#FFC83D'), seed=101)
STYLE_B = dict(over=hexc('#C9543D'), over_d=hexc('#A6422F'), shirt=hexc('#F7E9CF'), hat=hexc('#F6F1E4'),
               hat_l=hexc('#E4553F'), skin=hexc('#B9805E'), skin_d=hexc('#9A6446'), boot=hexc('#4A3036'),
               button=hexc('#F6F1E4'), seed=202)
INK = hexc('#2A1E26')
BLUSH = hexc('#F07C84')


# ------------------------------------------------------------------ IK
def ik(side, S, T, bend):
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = math.hypot(dx, dy)
    k = 1.0
    if d > (L1 + L2) * 0.98:
        k = min(d / ((L1 + L2) * 0.98), 1.6)
    l1, l2 = L1 * k, L2 * k
    d = clamp(d, abs(l1 - l2) + 1e-3, (l1 + l2) * 0.999)
    base = math.atan2(dx, dy)
    cg = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    g = math.acos(clamp(cg, -1, 1))
    th1 = base + bend * g
    ex, ey = S[0] + l1 * math.sin(th1), S[1] + l1 * math.cos(th1)
    th2 = math.atan2(T[0] - ex, T[1] - ey)
    if side > 0:
        return (th1, th2 - th1, k)
    return (-th1, -(th2 - th1), k)


def to_local(P, pt):
    x, y = pt[0] - P['x'], pt[1] - (P['y'] + P['bob'])
    c, s = math.cos(-P['lean']), math.sin(-P['lean'])
    return ((x * c - y * s) / CS, (x * s + y * c) / CS)


def shoulder(P, side):
    return (side * 23, -106 - 7 * P['shrug'])


def head_center_world(P):
    lx, ly = 0, -148 * CS
    c, s = math.cos(P['lean']), math.sin(P['lean'])
    return (P['x'] + lx * c - ly * s, P['y'] + P['bob'] + lx * s + ly * c)


def look_at(P, target, gain=1.15):
    h = head_center_world(P)
    dx, dy = target[0] - h[0], target[1] - h[1]
    n = math.hypot(dx, dy) + 1e-6
    return (clamp(dx / n * gain, -1, 1), clamp(dy / n * gain, -1, 1))


# arm specs: ('a', a_deg, b_deg[, wave_amp_deg, wave_hz]) | ('w', fn(t)->world pt, bend) | ('l', (x,y) local, bend)
def eval_spec(spec, side, P, t):
    if spec[0] == 'a':
        a, b = spec[1] * D2R, spec[2] * D2R
        if len(spec) > 3:
            b += spec[3] * D2R * math.sin(TAU * spec[4] * t)
        sw = P.get('swing', 0.0) * side
        return (a + sw, b + 0.5 * abs(sw), 1.0)
    if spec[0] == 'w':
        T = spec[1](t)
        if T is None:
            return (12 * D2R, 10 * D2R, 1.0)
        return ik(side, shoulder(P, side), to_local(P, T), spec[2])
    if spec[0] == 'l':
        T = spec[1] if not callable(spec[1]) else spec[1](t)
        return ik(side, shoulder(P, side), T, spec[2])
    raise ValueError(spec)


def eval_arms(keys, P, t):
    """keys: list of (time, specL, specR[, ease]). Returns ((aL,bL,kL),(aR,bR,kR))."""
    if t <= keys[0][0]:
        k0 = k1 = keys[0]
        w = 0
    else:
        k0 = k1 = keys[-1]
        w = 0
        for i in range(1, len(keys)):
            if t < keys[i][0]:
                k0, k1 = keys[i - 1], keys[i]
                e = k1[3] if len(k1) > 3 else 'io'
                w = EASES[e]((t - k0[0]) / (k1[0] - k0[0]))
                break
    out = []
    for idx, side in ((1, -1), (2, 1)):
        s0 = eval_spec(k0[idx], side, P, t)
        if w <= 0 or k0 is k1:
            out.append(s0)
            continue
        s1 = eval_spec(k1[idx], side, P, t)
        out.append(tuple(lerp(a, b, w) for a, b in zip(s0, s1)))
    return out


# ------------------------------------------------------------------ drawing
def draw_worker(c, st, P, t):
    seed = st['seed']
    # contact shadow
    c.save()
    c.translate(P['x'], P['y'] + 3)
    c.scale(1, 0.2)
    lift = clamp(-P['bob'] / 50)
    c.arc(0, 0, 38 * CS * (1 - 0.3 * lift), 0, TAU)
    c.set_source_rgba(*SHC, 0.28 * (1 - 0.5 * lift))
    c.fill()
    c.restore()

    c.save()
    c.translate(P['x'], P['y'] + P['bob'])
    c.rotate(P['lean'])
    sq = P['squash']
    c.scale(CS / math.sqrt(sq), CS * sq)

    # legs
    for i, side in enumerate((-1, 1)):
        ang = P['legs'][i]
        c.save()
        c.translate(side * 11, -52)
        c.rotate(-ang)
        rrect(c, -8, -4, 16, 48, 7)
        paper(c, st['over_d'] if side < 0 else st['over'], seed=seed + i, rim=0.15)
        rrect(c, -12 + side * 3, 38, 25, 14, 7)
        paper(c, st['boot'], seed=seed + 5 + i, rim=0.12)
        c.restore()

    # torso
    rrect(c, -26, -120, 52, 74, 18)
    paper(c, st['shirt'], seed=seed + 10)
    # overalls
    rrect(c, -27.5, -76, 55, 32, 11)
    paper(c, st['over'], seed=seed + 11, sh=(1.5, 2, 0.15))
    rrect(c, -15, -103, 30, 36, 6)
    paper(c, st['over'], seed=seed + 12, sh=(1.5, 2, 0.15))
    c.move_to(-12, -100)
    c.line_to(-21, -116 - 3 * P['shrug'])
    c.move_to(12, -100)
    c.line_to(21, -116 - 3 * P['shrug'])
    pstroke(c, st['over'], 6, sh=(1, 1.5, 0.15))
    rrect(c, -8, -94, 16, 12, 3)
    paper(c, st['over_d'], seed=seed + 13, sh=None, rim=0.1)
    for bx in (-10, 10):
        c.arc(bx, -97, 2.6, 0, TAU)
        c.set_source_rgb(*st['button'])
        c.fill()

    # head
    c.save()
    c.translate(0, -116)
    c.rotate(P['tilt'])
    c.translate(0, -32 - 2 * P['shrug'])
    lx, ly = P['look']
    fx, fy = lx * 9, ly * 5.5
    for side in (-1, 1):
        c.arc(side * 30 + fx * 0.15, 3, 7.5, 0, TAU)
        paper(c, st['skin_d'], seed=seed + 20, sh=None, rim=0.1)
    c.arc(0, 0, 31, 0, TAU)
    paper(c, st['skin'], seed=seed + 21)
    # cheeks
    for side in (-1, 1):
        c.save()
        c.translate(side * 19 + fx * 0.85, 12 + fy)
        c.scale(1, 0.62)
        c.arc(0, 0, 6.2, 0, TAU)
        c.restore()
        c.set_source_rgba(*BLUSH, 0.38)
        c.fill()
    # nose
    c.save()
    c.translate(fx * 1.3, 7 + fy)
    c.scale(1, 0.8)
    c.arc(0, 0, 4.2, 0, TAU)
    c.restore()
    c.set_source_rgb(*st['skin_d'])
    c.fill()
    draw_eyes(c, P, fx, fy)
    draw_mouth(c, P, fx, fy, t)
    # hard hat
    hx = fx * 0.35
    c.arc(hx, -11, 34, math.pi, TAU)
    c.close_path()
    paper(c, st['hat'], seed=seed + 30)
    rrect(c, hx - 6 + fx * 0.25, -43, 12, 32, 5)
    paper(c, st['hat_l'], seed=seed + 31, sh=None, rim=0.1)
    rrect(c, -41 + fx * 0.55, -15, 82, 9.5, 4.7)
    paper(c, shade(st['hat'], 0.9), seed=seed + 32, sh=(1.5, 2.5, 0.25))
    draw_brows(c, P, fx, fy)
    c.restore()

    # arms (after head so hands can come in front)
    for i, side in enumerate((-1, 1)):
        a, b, k = P['arms'][i]
        S = shoulder(P, side)
        th1 = side * a
        th2 = side * (a + b)
        E = (S[0] + L1 * k * math.sin(th1), S[1] + L1 * k * math.cos(th1))
        Hd = (E[0] + L2 * k * math.sin(th2), E[1] + L2 * k * math.cos(th2))
        c.move_to(*S)
        c.line_to(*E)
        c.line_to(*Hd)
        pstroke(c, shade(st['shirt'], 0.94), 12.5, sh=(1.8, 2.6, 0.22))
        # mitten hand with thumb
        c.arc(Hd[0], Hd[1], 8.6, 0, TAU)
        paper(c, st['skin'], seed=seed + 40 + i, sh=(1.5, 2, 0.2), rim=0.12)
        tx = Hd[0] + side * 6 * math.cos(th2) - 2 * math.sin(th2)
        ty = Hd[1] - side * 6 * math.sin(th2) - 2 * math.cos(th2)
        c.arc(tx, ty, 3.8, 0, TAU)
        paper(c, st['skin'], seed=seed + 44 + i, sh=None, rim=0.1)
    c.restore()


def draw_eyes(c, P, fx, fy):
    kind = P['eyes']
    blink = P['blink']
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for side in (-1, 1):
        ex, ey = side * 11 + fx, 2 + fy
        if kind == 'n' and blink > 0.6:
            kind_s = 'closed'
        else:
            kind_s = kind
        if kind_s == 'n':
            c.save()
            c.translate(ex, ey)
            c.scale(1, max(0.15, 1 - blink))
            c.arc(0, 0, 4.4, 0, TAU)
            c.restore()
            c.save()
            c.translate(ex, ey)
            c.scale(1, 1.32 * max(0.15, 1 - blink))
            c.arc(0, 0, 4.4, 0, TAU)
            c.restore()
            c.set_source_rgb(*INK)
            c.fill()
            c.arc(ex + 1.4, ey - 2.2, 1.4, 0, TAU)
            c.set_source_rgba(1, 1, 1, 0.9 * (1 - blink))
            c.fill()
        elif kind_s == 'closed':
            c.move_to(ex - 4.5, ey + 1)
            c.line_to(ex + 4.5, ey + 1)
            c.set_source_rgb(*INK)
            c.set_line_width(2.6)
            c.stroke()
        elif kind_s == 'happy':
            c.arc(ex, ey + 3, 5, math.pi + 0.35, TAU - 0.35)
            c.set_source_rgb(*INK)
            c.set_line_width(2.8)
            c.stroke()
        elif kind_s == 'squeeze':
            c.move_to(ex - side * 5, ey - 4)
            c.line_to(ex + side * 4, ey)
            c.line_to(ex - side * 5, ey + 4)
            c.set_source_rgb(*INK)
            c.set_line_width(2.6)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke()
        elif kind_s == 'wide':
            c.arc(ex, ey, 7.4, 0, TAU)
            c.set_source_rgb(1, 1, 0.98)
            c.fill_preserve()
            c.set_source_rgb(*INK)
            c.set_line_width(1.6)
            c.stroke()
            lx, ly = P['look']
            c.arc(ex + lx * 2.6, ey + ly * 2.6, 3.8, 0, TAU)
            c.set_source_rgb(*INK)
            c.fill()
            c.arc(ex + lx * 2.6 + 1.3, ey + ly * 2.6 - 1.4, 1.2, 0, TAU)
            c.set_source_rgb(1, 1, 1)
            c.fill()


def draw_brows(c, P, fx, fy):
    br = P['brow']
    worry = P.get('worry', 0.0)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for side in (-1, 1):
        ex, ey = side * 11 + fx, -8.5 + fy - br * 6
        tilt = side * worry * 0.35
        c.save()
        c.translate(ex, ey)
        c.rotate(tilt)
        c.move_to(-5, 0.8)
        c.curve_to(-2, -1.4, 2, -1.4, 5, 0.8)
        c.restore()
        c.set_source_rgb(*INK)
        c.set_line_width(2.4)
        c.stroke()


def draw_mouth(c, P, fx, fy, t):
    kind = P['mouth']
    mx, my = fx * 1.15, 17 + fy * 0.7
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgb(*INK)
    if kind == 'smile':
        c.arc(mx, my - 5, 7.5, 0.22 * math.pi, 0.78 * math.pi)
        c.set_line_width(2.6)
        c.stroke()
    elif kind == 'small':
        c.arc(mx, my - 4, 5, 0.25 * math.pi, 0.75 * math.pi)
        c.set_line_width(2.4)
        c.stroke()
    elif kind == 'grin':
        c.move_to(mx - 9, my - 3)
        c.arc_negative(mx, my - 3, 9, math.pi, 0)
        c.close_path()
        c.fill()
        c.save()
        c.arc(mx, my - 3, 9, 0, math.pi)
        c.clip()
        c.arc(mx, my + 5, 5.5, 0, TAU)
        c.set_source_rgb(*hexc('#E86A6A'))
        c.fill()
        c.restore()
    elif kind in ('o', 'O'):
        s = 1.0 if kind == 'o' else 1.35
        c.save()
        c.translate(mx, my)
        c.scale(4.6 * s, 6 * s)
        c.arc(0, 0, 1, 0, TAU)
        c.restore()
        c.fill()
    elif kind == 'flat':
        c.move_to(mx - 5.5, my)
        c.line_to(mx + 5.5, my)
        c.set_line_width(2.5)
        c.stroke()
    elif kind == 'grit':
        rrect(c, mx - 8, my - 4, 16, 8, 2.5)
        c.set_source_rgb(1, 1, 0.97)
        c.fill_preserve()
        c.set_source_rgb(*INK)
        c.set_line_width(1.8)
        c.stroke()
        c.move_to(mx - 8, my)
        c.line_to(mx + 8, my)
        c.set_line_width(1.2)
        c.stroke()
    elif kind == 'wobble':
        c.move_to(mx - 7, my)
        for i in range(1, 8):
            xx = mx - 7 + i * 2
            c.line_to(xx, my + (1.6 if i % 2 else -1.6))
        c.set_line_width(2.3)
        c.stroke()


# ------------------------------------------------------------------ helpers for targets
def sun_pt(ang_deg):
    def f(t):
        s = sun_state(t)
        a = ang_deg * D2R
        return (s['x'] + SUNR * math.cos(a), s['y'] - SUNR * math.sin(a))
    return f


def crank_knob(t):
    th = -belt_offset(t) / 13.0 + 0.6
    return (CRANK_C[0] + 21 * math.cos(th), CRANK_C[1] + 21 * math.sin(th))


def pole_grip(who, which):
    def f(t):
        return grip_world(pole_state(t, who), which)
    return f


def sun_center(t):
    s = sun_state(t)
    return (s['x'], s['y'])


def roller_center(who):
    def f(t):
        return pole_points(pole_state(t, who))[2]
    return f


def jar_center(t):
    return jar_state(t)['c']


def sky_scan(t):
    # a point wandering over the sky while the stars scatter
    k = seg(t, 15.1, 17.2)
    return (lerp(580, 360, e_io(k)) + 160 * math.sin(k * 5), lerp(1300, 420, e_o(k * 1.4)))


# ------------------------------------------------------------------ choreography
IDLE = ('a', 12, 10)
READY = ('a', 38, 55)
UPV = ('a', 152, 12)
SHRUG = ('a', 30, 78)

A_ARMS = [
    (0.0, IDLE, IDLE),
    (0.55, IDLE, IDLE),
    (0.9, READY, READY),
    (1.15, READY, READY),
    (1.45, ('w', sun_pt(240), -1), ('w', sun_pt(225), -1)),
    (4.45, ('w', sun_pt(240), -1), ('w', sun_pt(225), -1)),
    (4.7, IDLE, ('l', (6, -168), -1)),                      # wipe brow
    (4.85, IDLE, ('l', (-16, -166), -1), 'lin'),
    (5.0, IDLE, ('l', (8, -170), -1), 'lin'),
    (5.25, IDLE, IDLE),
    (5.45, IDLE, IDLE),
    (5.62, ('w', pole_grip('A', 1), -1), ('w', pole_grip('A', 0), -1)),
    (8.72, ('w', pole_grip('A', 1), -1), ('w', pole_grip('A', 0), -1)),
    (8.95, IDLE, IDLE),
    (9.2, IDLE, ('a', 160, 30, 26, 1.6)),                  # signalling "up, up!"
    (10.5, IDLE, ('a', 160, 30, 26, 1.6)),
    (10.75, IDLE, IDLE),
    (11.0, ('a', 60, 40), ('a', 60, 40)),
    (11.12, UPV, UPV, 'o'),
    (11.45, UPV, UPV),
    (11.75, ('l', (4, -96), 1), ('l', (-4, -96), 1)),       # clasp hands, admiring
    (14.25, ('l', (4, -96), 1), ('l', (-4, -96), 1)),
    (14.42, ('l', (-27, -140), 1), ('l', (27, -140), -1), 'o'),  # hands to cheeks
    (15.1, ('l', (-27, -140), 1), ('l', (27, -140), -1)),
    (15.5, ('l', (2, -98), 1), ('l', (-2, -98), 1)),
    (16.9, ('l', (2, -98), 1), ('l', (-2, -98), 1)),
    (17.35, IDLE, IDLE),
    (18.2, IDLE, IDLE),
    (18.5, SHRUG, SHRUG, 'back'),
]

B_ARMS = [
    (0.0, IDLE, IDLE),
    (0.55, IDLE, IDLE),
    (0.9, READY, READY),
    (1.15, READY, READY),
    (1.4, ('l', (-28, -64), -1), ('w', crank_knob, -1)),
    (4.45, ('l', (-28, -64), -1), ('w', crank_knob, -1)),
    (4.62, ('l', (-30, -62), -1), ('l', (30, -62), 1)),     # hands on hips, proud
    (4.8, IDLE, IDLE),
    (5.32, IDLE, IDLE),
    (5.52, ('w', pole_grip('B', 1), -1), ('w', pole_grip('B', 0), -1)),
    (8.72, ('w', pole_grip('B', 1), -1), ('w', pole_grip('B', 0), -1)),
    (8.95, ('l', (4, -94), 1), ('l', (-4, -94), 1)),        # hands together, excited
    (10.8, ('l', (4, -94), 1), ('l', (-4, -94), 1)),
    (11.0, ('a', 60, 40), ('a', 60, 40)),
    (11.12, UPV, UPV, 'o'),
    (11.45, UPV, UPV),
    (11.8, ('l', (-30, -62), -1), ('l', (30, -62), 1)),     # hands on hips, backing up proudly
    (13.93, ('l', (-30, -62), -1), ('l', (30, -62), 1)),
    (14.1, ('a', 150, 25), ('a', 150, 25), 'o'),            # !!
    (14.5, ('a', 150, 25), ('a', 150, 25)),
    (14.72, ('a', 70, 20), ('a', 95, 5)),                   # reaching for the jar
    (15.0, ('a', 70, 20), ('a', 95, 5)),
    (15.35, ('a', 118, 40), ('a', 118, 40)),
    (16.9, ('a', 70, 40), ('a', 70, 40)),
    (17.35, IDLE, IDLE),
    (18.25, IDLE, IDLE),
    (18.55, SHRUG, SHRUG, 'back'),
]


class Actor:
    def __init__(self, name, style, row, xt, arms, looks, eyes, mouths, brows, tilts, leans, hops, shrugs, blinks, worry=None):
        self.name, self.st, self.row, self.xt, self.arms = name, style, row, xt, arms
        self.looks, self.eyes, self.mouths, self.brows = looks, eyes, mouths, brows
        self.tilts, self.leans, self.hops, self.shrugs, self.blinks = tilts, leans, hops, shrugs, blinks
        self.worry = worry

    def _blink(self, t):
        b = 0.0
        for tb in self.blinks:
            if tb <= t < tb + 0.14:
                k = (t - tb) / 0.14
                b = max(b, 1 - abs(2 * k - 1))
        return b


def make_look(keys):
    def resolve(P, t, v):
        if isinstance(v, tuple) and isinstance(v[0], str):
            return look_at(P, v[1](t))
        return v

    def f(P, t):
        if t <= keys[0][0]:
            return resolve(P, t, keys[0][1])
        for i in range(1, len(keys)):
            if t < keys[i][0]:
                k0, k1 = keys[i - 1], keys[i]
                w = e_io((t - k0[0]) / (k1[0] - k0[0]))
                a, b = resolve(P, t, k0[1]), resolve(P, t, k1[1])
                return (lerp(a[0], b[0], w), lerp(a[1], b[1], w))
        return resolve(P, t, keys[-1][1])
    return f


def _hops(keys):
    """keys: list of (t_start, height, dur). Returns (yoffset, squash)."""
    def f(t):
        y, sq = 0.0, 1.0
        for ts, hgt, dur in keys:
            # anticipation squash, released smoothly into the jump
            if ts - 0.14 <= t < ts:
                k = seg(t, ts - 0.14, ts)
                sq = min(sq, 1 - 0.1 * math.sin(k * math.pi))
            if ts <= t < ts + dur:
                k = (t - ts) / dur
                y = -hgt * 4 * k * (1 - k)
                sq = max(sq, 1 + 0.06 * math.sin(k * math.pi))
            if ts + dur <= t < ts + dur + 0.14:
                k = seg(t, ts + dur, ts + dur + 0.14)
                sq = min(sq, 1 - 0.1 * math.sin(k * math.pi))
        return y, sq
    return f


# look keys (lx, ly) or ('at', fn)
A_LOOK = make_look([
    (0.0, (-0.9, 0.05)), (0.3, (-0.9, 0.05)), (0.5, ('at', sun_center)),
    (4.45, ('at', sun_center)), (4.7, (0.1, 0.1)), (5.0, (0.1, 0.1)), (5.15, (0.9, 0.2)),
    (5.45, (0.5, 0.7)), (5.7, (0.5, 0.7)), (6.0, ('at', roller_center('A'))), (8.2, ('at', roller_center('A'))),
    (8.4, (-0.4, 0.4)), (8.75, (-0.4, 0.4)), (8.95, ('at', sun_center)), (13.9, ('at', sun_center)),
    (14.2, ('at', jar_center)), (15.05, ('at', jar_center)), (15.3, ('at', sky_scan)), (17.1, ('at', sky_scan)),
    (17.45, (1.0, 0.05)), (18.2, (1.0, 0.05)), (18.45, (0.15, 0.25)),
])
B_LOOK = make_look([
    (0.0, (0.9, 0.05)), (0.3, (0.9, 0.05)), (0.5, ('at', sun_center)),
    (1.4, ('at', crank_knob)), (1.9, ('at', sun_center)), (4.45, ('at', sun_center)), (4.7, (0.0, 0.1)),
    (4.85, (0.95, 0.1)), (5.3, (0.9, 0.1)), (5.45, (0.3, 0.7)), (5.7, (0.3, 0.7)),
    (5.95, ('at', roller_center('B'))), (8.2, ('at', roller_center('B'))), (8.4, (0.5, 0.4)), (8.75, (0.5, 0.4)),
    (8.95, ('at', sun_center)), (13.95, ('at', sun_center)), (14.12, (0.95, 0.35)), (14.3, ('at', jar_center)),
    (15.05, ('at', jar_center)), (15.3, ('at', sky_scan)), (17.1, ('at', sky_scan)),
    (17.5, (-1.0, 0.05)), (18.25, (-1.0, 0.05)), (18.5, (-0.15, 0.25)),
])


def make_actor(name):
    if name == 'A':
        return Actor(
            'A', STYLE_A, ROW_A, A_X, A_ARMS, A_LOOK,
            eyes=Steps((0, 'n'), (1.35, 'squeeze'), (4.5, 'n'), (4.72, 'happy'), (5.0, 'n'), (6.2, 'happy'),
                       (6.6, 'n'), (11.0, 'happy'), (13.95, 'n'), (14.32, 'wide'), (15.2, 'wide'), (17.35, 'n'),
                       (18.45, 'happy'), (19.55, 'n')),
            mouths=Steps((0, 'smile'), (0.7, 'o'), (1.35, 'grit'), (4.5, 'o'), (4.72, 'smile'), (6.3, 'grin'),
                         (8.2, 'smile'), (9.0, 'o'), (10.95, 'grin'), (11.7, 'smile'), (14.32, 'O'),
                         (15.3, 'o'), (17.35, 'flat'), (18.45, 'wobble')),
            brows=Track((0, 0.2), (0.6, 0.2), (0.8, 1.0), (1.3, 0.4), (1.4, -0.3), (4.45, -0.3), (4.6, 0.3),
                        (14.2, 0.3), (14.35, 1.2, 'o'), (17.2, 1.0), (17.45, 0.2), (18.3, 0.2), (18.55, 1.2, 'back')),
            tilts=Track((0, 0.0), (0.3, 0.08), (0.55, 0.0), (11.6, 0.0), (12.2, -0.12), (12.8, -0.02), (13.4, -0.12),
                        (13.95, 0.0), (18.25, 0.0), (18.55, -0.14, 'back')),
            leans=Track((0, 0.0), (1.15, 0.0), (1.45, 0.1), (4.45, 0.1), (4.7, -0.05), (5.0, 0.0),
                        (PT0, 0.0), (6.9, -0.06), (PT1, -0.1), (8.5, 0.0), (14.3, 0.0), (14.45, -0.08, 'o'), (15.0, 0.0)),
            hops=_hops([(0.72, 16, 0.26), (11.02, 46, 0.42)]),
            shrugs=Track((0, 0.0), (18.2, 0.0), (18.5, 1.0, 'back'), (18.95, 0.55), (19.25, 1.0), (19.6, 0.7)),
            blinks=[2.1, 5.9, 8.9, 12.5, 16.0, 17.9, 19.7],
            worry=Track((0, 0.0), (14.3, 0.0), (14.45, 1.0), (17.3, 1.0), (17.5, 0.0), (18.4, 0.0), (18.6, 0.8)),
        )
    return Actor(
        'B', STYLE_B, ROW_B, B_X, B_ARMS, B_LOOK,
        eyes=Steps((0, 'n'), (1.5, 'squeeze'), (4.5, 'n'), (4.6, 'happy'), (4.85, 'n'), (6.3, 'happy'), (6.8, 'n'),
                   (11.0, 'happy'), (13.93, 'n'), (14.05, 'wide'), (15.25, 'wide'), (17.4, 'n'), (18.55, 'n')),
        mouths=Steps((0, 'smile'), (0.7, 'o'), (1.5, 'grit'), (4.5, 'grin'), (4.85, 'smile'), (6.3, 'o'),
                     (6.8, 'grin'), (8.3, 'smile'), (10.95, 'grin'), (11.7, 'smile'), (13.93, 'O'),
                     (15.3, 'o'), (17.4, 'flat'), (18.55, 'wobble')),
        brows=Track((0, 0.2), (0.6, 0.2), (0.8, 1.0), (1.3, 0.4), (1.5, -0.3), (4.45, -0.3), (4.6, 0.4),
                    (13.93, 0.4), (14.05, 1.3, 'o'), (17.2, 1.0), (17.5, 0.2), (18.35, 0.2), (18.6, 1.3, 'back')),
        tilts=Track((0, 0.0), (0.3, -0.08), (0.55, 0.0), (11.6, 0.0), (12.3, 0.1), (13.0, 0.02), (13.6, 0.1),
                    (13.93, 0.0), (18.3, 0.0), (18.6, 0.14, 'back')),
        leans=Track((0, 0.0), (1.3, 0.0), (1.5, 0.08), (4.45, 0.08), (4.6, -0.06), (4.85, 0.0), (PT0, 0.0),
                    (PT1, 0.08), (8.5, 0.0), (12.55, 0.0), (12.9, -0.07), (BUMP_T, -0.07), (BUMP_T + 0.05, 0.12, 'o'),
                    (14.3, 0.0)),
        hops=_hops([(0.72, 16, 0.26), (11.02, 46, 0.42), (14.86, 22, 0.24)]),
        shrugs=Track((0, 0.0), (18.25, 0.0), (18.55, 1.0, 'back'), (19.0, 0.55), (19.3, 1.0), (19.65, 0.7)),
        blinks=[3.0, 7.4, 10.2, 13.1, 16.4, 17.95, 19.85],
        worry=Track((0, 0.0), (14.05, 0.0), (14.2, 1.0), (17.35, 1.0), (17.55, 0.0), (18.45, 0.0), (18.65, 1.0)),
    )


ACTOR_A = make_actor('A')
ACTOR_B = make_actor('B')


def _pose(self, t):
    x = self.xt(t)
    dt = 1 / 60
    v = (self.xt(t + dt) - self.xt(t - dt)) / (2 * dt)
    amp = clamp(abs(v) / 120)
    phase = x * TAU / 80
    legs = (0.42 * amp * math.sin(phase), -0.42 * amp * math.sin(phase))
    hop, squash = self.hops(t)
    bob = -4 * amp * abs(math.sin(phase)) + hop
    squash *= 1 + 0.012 * math.sin(t * 2.6 + (1 if self.name == 'A' else 2.4))
    extra_bob = 0.0
    if self.name == 'B' and 1.4 <= t < 4.45:
        th = -belt_offset(t) / 13.0
        extra_bob = 2.0 * math.sin(th)
    P = dict(x=x, y=self.row, bob=bob + extra_bob, lean=self.leans(t), squash=squash, legs=legs,
             shrug=self.shrugs(t), tilt=self.tilts(t), swing=0.35 * amp * math.sin(phase))
    P['brow'] = self.brows(t)
    P['worry'] = self.worry(t) if self.worry else 0.0
    P['look'] = (0.0, 0.0)
    P['look'] = self.looks(P, t)
    P['eyes'] = self.eyes(t)
    P['mouth'] = self.mouths(t)
    P['blink'] = self._blink(t)
    P['arms'] = eval_arms(self.arms, P, t)
    return P


Actor.pose = _pose

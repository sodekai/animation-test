"""World timeline: where the sun, crane, poles, jar and stars are at time t."""
import math
import numpy as np
from core import *

# ---------------------------------------------------------------- layout
SUNX, SUNY, SUNR = 540, 560, 88
BELT_X0, BELT_X1, BELT_TOP = 150, 835, 1380
SUN_BELT_Y = BELT_TOP - SUNR
SUN_START_X, SUN_END_X = 270, 745
ROW_A, ROW_B = 1478, 1505
FRONT_Y = 1565
CRANE_P = (580, 1112)
HOOK_TO_SUN = 114
PINK_BUCKET_X, ORANGE_BUCKET_X = 380, 670
BUCKET_BOTTOM = 1470
CRATE_X, CRATE_Y, CRATE_W, CRATE_H = 745, 1455, 110, 105
JAR_PIVOT = (743, 1455)
CRANK_C = (167, 1397)
PINK_Y, ORANGE_Y = 330, 790
PT0, PT1 = 6.35, 8.1          # painting sweep
NIGHT_T0, NIGHT_T1 = 15.2, 17.5
BUMP_T = 13.93
CHAR_S = 1.12


# ---------------------------------------------------------------- sun on the belt
def sun_belt_x(t):
    if t < 1.4:
        return SUN_START_X
    if t < 4.45:
        u = seg(t, 1.4, 4.45)
        return SUN_START_X + (SUN_END_X - SUN_START_X) * u * u * (2 - u)
    k = seg(t, 4.45, 4.85)
    return SUN_END_X - 9 * math.sin(math.pi * k) * (1 - 0.3 * k)


def belt_offset(t):
    return sun_belt_x(min(t, 4.45)) - SUN_START_X


# ---------------------------------------------------------------- crane
REST_TIP = (674, 935)
TIPX = Track((0, 674), (8.45, 674), (9.05, 745), (9.35, 745), (9.8, 728), (10.75, 540), (11.3, 540), (12.1, 674))
TIPY = Track((0, 935), (8.45, 935), (9.05, 840), (9.35, 840), (10.45, 420), (10.75, 400, 'o'), (11.3, 400), (12.1, 935))
CABLE = Track((0, 40), (8.45, 40), (9.05, 338), (9.35, 338), (10.6, 46), (11.05, 46), (11.45, 28))
CLAW = Track((0, 1.0), (9.0, 1.0), (9.22, 0.0, 'o'), (11.0, 0.0), (11.2, 1.0, 'o'))


def _sim_swing():
    dt = 1 / 600
    ts = np.arange(9.30, 11.2, dt)
    phi, om = 0.0, 0.0
    out = []
    g = 2400.0
    for t in ts:
        ax = (TIPX(t + dt) - 2 * TIPX(t) + TIPX(t - dt)) / (dt * dt)
        ay = (TIPY(t + dt) - 2 * TIPY(t) + TIPY(t - dt)) / (dt * dt)
        l = CABLE(t) + HOOK_TO_SUN
        ld = (CABLE(t + dt) - CABLE(t - dt)) / (2 * dt)
        acc = (-ax * math.cos(phi) - (g - ay) * math.sin(phi) - 2 * ld * om) / l - 1.6 * om
        om += acc * dt
        phi += om * dt
        out.append(phi)
    return ts, np.array(out)


_SW_T, _SW_P = _sim_swing()


def swing(t):
    if t < 9.3 or t > 11.2:
        return 0.0
    p = float(np.interp(t, _SW_T, _SW_P))
    return p * (1 - e_io(seg(t, 10.5, 10.88)))


def crane_state(t):
    tip = (TIPX(t), TIPY(t))
    return dict(tip=tip, cable=CABLE(t), claw=CLAW(t), phi=swing(t) if t < 11.0 else 0.0)


# ---------------------------------------------------------------- sun state
def sun_state(t):
    rot = (sun_belt_x(min(t, 9.3)) - SUN_START_X) / SUNR
    if t < 9.3:
        x, y = sun_belt_x(t), SUN_BELT_Y
        # a little jiggle when the claw bites
        j = seg(t, 9.1, 9.3)
        y -= 4 * math.sin(math.pi * j)
    elif t < 10.9:
        tip = (TIPX(t), TIPY(t))
        l = CABLE(t) + HOOK_TO_SUN
        ph = swing(t)
        x, y = tip[0] + l * math.sin(ph), tip[1] + l * math.cos(ph)
        w = e_io(seg(t, 10.6, 10.9))
        x, y = lerp(x, SUNX, w), lerp(y, SUNY, w)
    else:
        x, y = SUNX, SUNY
    rot = rot - 0.25 * e_io(seg(t, 9.4, 10.8))
    placed = t >= 10.98
    rays = e_back(seg(t, 11.0, 11.5), 2.4)
    flash = e_o(seg(t, 10.97, 11.07)) * math.exp(-max(0.0, t - 11.07) * 3.2)
    moon = e_io(seg(t, 15.9, 17.3))
    squash = 1.0
    if 10.98 <= t < 11.4:
        k = seg(t, 10.98, 11.4)
        squash = 1 + 0.08 * math.sin(k * math.pi * 2) * (1 - k)
    front = t < 12.0      # drawn in front of the factory until the boom is back at rest
    return dict(x=x, y=y, rot=rot, rays=rays, flash=flash, moon=moon, front=front, placed=placed,
                squash=squash)


# ---------------------------------------------------------------- paint rollers
def pink_rx(t):
    return lerp(-110, 1190, e_s(seg(t, PT0, PT1)))


def orange_rx(t):
    return lerp(1190, -110, e_s(seg(t, PT0 + 0.08, PT1 + 0.05)))


_PT = np.linspace(PT0 + 1e-4, PT1 - 1e-4, 900)
_PX = np.array([pink_rx(t) for t in _PT])
_PTo = np.linspace(PT0 + 0.08 + 1e-4, PT1 + 0.05 - 1e-4, 900)
_OX = np.array([orange_rx(t) for t in _PTo])


def pink_tpass(x):
    return np.interp(x, _PX, _PT, left=PT0, right=1e9)


def orange_tpass(x):
    return np.interp(-np.asarray(x), -_OX, _PTo, left=PT0, right=1e9)


# ---------------------------------------------------------------- worker x tracks (needed by poles)
def fA_push(t):
    return sun_belt_x(t) - 125


A_X = Track((0, 150), (1.1, 150), (1.45, fA_push), (4.45, fA_push, 'lin'), (4.85, fA_push, 'lin'),
            (5.05, 620), (5.5, 640), (PT0, 640), (PT1, 450, 's'))
B_X = Track((0, 95), (4.5, 95), (5.45, 350), (PT0, 350), (PT1, 590, 's'), (12.55, 590),
            (12.9, 604, 'i2'), (BUMP_T, 700, 'lin'), (14.08, 690, 'o'))


def grip_point(wx, row):
    return (wx + 24 * CHAR_S, row - 92 * CHAR_S)


def _dirv(phi):
    return (math.sin(phi), -math.cos(phi))


def _perp(phi):
    return (math.cos(phi), math.sin(phi))


def _aim(C, R):
    """Pole angle/length from grip C so that the roller centre lands on R."""
    phi = math.atan2(R[0] - C[0], C[1] - R[1])
    for _ in range(3):
        d, p = _dirv(phi), _perp(phi)
        E = (R[0] - p[0] * 24 + d[0] * 34, R[1] - p[1] * 24 + d[1] * 34)
        phi = math.atan2(E[0] - C[0], C[1] - E[1])
    d = _dirv(phi)
    p = _perp(phi)
    E = (R[0] - p[0] * 24 + d[0] * 34, R[1] - p[1] * 24 + d[1] * 34)
    La = math.hypot(E[0] - C[0], E[1] - C[1])
    return phi, La


def _angle_lerp(a, b, w):
    return a + (b - a) * w


def pole_state(t, who):
    """Returns dict(C, phi, La, Lb, grips=(g_top, g_low) or None, color, roller)."""
    if who == 'B':
        bx, row, xt, R_fn, flip_to, lean_base, lean_phi = PINK_BUCKET_X, ROW_B, B_X, (lambda tt: (pink_rx(tt), PINK_Y)), 1, (626, 1476), 10 * D2R
    else:
        bx, row, xt, R_fn, flip_to, lean_base, lean_phi = ORANGE_BUCKET_X, ROW_A, A_X, (lambda tt: (orange_rx(tt), ORANGE_Y)), -1, (414, 1474), -10 * D2R
    Lb = 62
    La0 = 72
    C_b = (bx + 24, 1384)
    t_pull, t_flip, t_ext, t_ret, t_lean, t_rel = 5.55, 5.75, 6.05, PT1 + 0.02, 8.45, 8.78
    if who == 'A':
        t_pull, t_flip, t_ext = 5.6, 5.8, 6.08
    g_handle = (-50, -26)
    g_roll = (6, -24)
    if t < t_pull:
        return dict(C=C_b, phi=math.pi, La=La0, Lb=Lb, grips=g_handle)
    if t < t_flip:
        k = e_o(seg(t, t_pull, t_flip))
        return dict(C=(C_b[0], lerp(C_b[1], 1322, k)), phi=math.pi, La=La0, Lb=Lb, grips=g_handle)
    # start aim
    G0 = grip_point(xt(PT0), row)
    phi0, L0 = _aim(G0, R_fn(PT0))
    if t < t_ext:
        k = e_io(seg(t, t_flip, t_ext))
        G = grip_point(xt(t), row)
        C = (lerp(C_b[0], G[0], k), lerp(1322, G[1], k))
        target = phi0 if flip_to < 0 else phi0 + TAU
        phi = lerp(math.pi, target, k)
        g = (lerp(g_handle[0], g_roll[0], k), lerp(g_handle[1], g_roll[1], k))
        return dict(C=C, phi=phi, La=La0, Lb=Lb, grips=g)
    if t < PT0:
        k = seg(t, t_ext, PT0)
        # telescoping happens in 3 clacky steps
        steps = 3
        kk = (math.floor(k * steps) + e_o(min(1, (k * steps % 1) * 1.6))) / steps if k < 1 else 1
        G = grip_point(xt(t), row)
        phi = phi0
        return dict(C=G, phi=phi, La=lerp(La0, L0, kk), Lb=Lb, grips=g_roll)
    if t < t_ret:
        G = grip_point(xt(t), row)
        phi, L = _aim(G, R_fn(t))
        return dict(C=G, phi=phi, La=L, Lb=Lb, grips=g_roll)
    G1 = grip_point(xt(t_ret), row)
    phi1, L1 = _aim(G1, R_fn(t_ret))
    if t < t_lean:
        k = seg(t, t_ret, t_lean)
        steps = 3
        kk = (math.floor(k * steps) + e_o(min(1, (k * steps % 1) * 1.6))) / steps if k < 1 else 1
        G = grip_point(xt(t), row)
        return dict(C=G, phi=lerp(phi1, 0, e_io(k)), La=lerp(L1, La0, kk), Lb=Lb, grips=g_roll)
    # lean against the conveyor
    Cl = (lean_base[0] + Lb * math.sin(lean_phi), lean_base[1] - Lb * math.cos(lean_phi))
    G = grip_point(xt(t_lean), row)
    k = e_io(seg(t, t_lean, t_rel - 0.05))
    C = (lerp(G[0], Cl[0], k), lerp(G[1], Cl[1], k))
    return dict(C=C, phi=lerp(0, lean_phi, k), La=La0, Lb=Lb, grips=g_roll)


def pole_points(ps):
    C, phi, La, Lb = ps['C'], ps['phi'], ps['La'], ps['Lb']
    d, p = _dirv(phi), _perp(phi)
    E = (C[0] + d[0] * La, C[1] + d[1] * La)
    Bt = (C[0] - d[0] * Lb, C[1] - d[1] * Lb)
    Rc = (E[0] + p[0] * 24 - d[0] * 34, E[1] + p[1] * 24 - d[1] * 34)
    return E, Bt, Rc, d, p


def grip_world(ps, which):
    if ps is None or ps.get('grips') is None:
        return None
    d = _dirv(ps['phi'])
    off = ps['grips'][which]
    return (ps['C'][0] + d[0] * off, ps['C'][1] + d[1] * off)


# ---------------------------------------------------------------- jar
JAR_PSI = Track((0, 0), (BUMP_T + 0.02, 0), (14.12, 13 * D2R, 'o'), (14.3, -7 * D2R, 'io'),
                (14.46, 19 * D2R, 'io'), (14.62, 42 * D2R, 'i2'))
CRATE_DX = Track((0, 0), (BUMP_T, 0), (BUMP_T + 0.06, 7, 'o'), (14.25, 0, 'io'))
JAR_LAND_T, JAR_ROLL_T1 = 14.86, 15.25
JAR_LAND_X, JAR_STOP_X, JAR_GROUND_CY = 690, 625, FRONT_Y - 35


def _rot_ccw(v, a):
    return (v[0] * math.cos(a) + v[1] * math.sin(a), -v[0] * math.sin(a) + v[1] * math.cos(a))


def jar_state(t):
    """Jar centre (world), angle psi (visual CCW), popped flag."""
    if t < 14.62:
        psi = JAR_PSI(t)
        dx = CRATE_DX(t)
        pv = (JAR_PIVOT[0] + dx, JAR_PIVOT[1])
        v = _rot_ccw((35, -46), psi)
        return dict(c=(pv[0] + v[0], pv[1] + v[1]), psi=psi, popped=False)
    v = _rot_ccw((35, -46), 42 * D2R)
    c1 = (JAR_PIVOT[0] + v[0], JAR_PIVOT[1] + v[1])
    if t < JAR_LAND_T:
        k = seg(t, 14.62, JAR_LAND_T)
        x = lerp(c1[0], JAR_LAND_X, k)
        y = lerp(c1[1], JAR_GROUND_CY, k * k)
        psi = lerp(42 * D2R, 90 * D2R, e_o2(k))
        return dict(c=(x, y), psi=psi, popped=False)
    k = seg(t, JAR_LAND_T, JAR_ROLL_T1)
    x = lerp(JAR_LAND_X, JAR_STOP_X, e_o(k))
    hop = 10 * max(0.0, math.sin(math.pi * seg(t, JAR_LAND_T, JAR_LAND_T + 0.14)))
    wob = 5 * D2R * math.sin(seg(t, JAR_LAND_T, 15.45) * math.pi * 3) * (1 - seg(t, JAR_LAND_T, 15.45))
    return dict(c=(x, JAR_GROUND_CY - hop), psi=90 * D2R + wob, popped=t >= 15.05)


def jar_mouth(t):
    js = jar_state(t)
    v = _rot_ccw((0, -52), js['psi'])
    return (js['c'][0] + v[0], js['c'][1] + v[1])


# ---------------------------------------------------------------- stars
STAR_T0 = 15.08


def _make_stars():
    rng = np.random.default_rng(42)
    pts = []
    cols, rows = 8, 10
    for r in range(rows):
        for q in range(cols):
            x = 40 + (q + rng.uniform(0.1, 0.9)) * (1000 / cols)
            y = 45 + (r + rng.uniform(0.1, 0.9)) * (840 / rows)
            if math.hypot(x - SUNX, y - SUNY) < 175:
                continue
            if 150 < x < 430 and y > 560:      # chimney smoke
                continue
            if 560 < x < 760 and y > 800:      # crane boom at rest
                continue
            pts.append((x, y))
    rng.shuffle(pts)
    stars = []
    M = (JAR_STOP_X - 52, JAR_GROUND_CY)
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        u = rng.random()
        size = 7 + 7 * u ** 2 + (7 if rng.random() < 0.12 else 0)
        s0 = STAR_T0 + 0.95 * (i / n) ** 1.15 + rng.uniform(0, 0.05)
        d = rng.uniform(1.05, 1.6)
        P1 = (M[0] - 60 - 170 * rng.random(), M[1] - 260 - 220 * rng.random())
        P2 = (x + (x - SUNX) * 0.3 * rng.random(), y + 200 + 180 * rng.random())
        col = [hexc('#FFF4C2'), hexc('#FFFFFF'), hexc('#FFE08A'), hexc('#FFF0A8')][int(rng.integers(0, 4))]
        stars.append(dict(E=(x, y), M=M, P1=P1, P2=P2, s0=s0, d=d, size=size, rot0=rng.uniform(0, TAU),
                          spin=rng.uniform(-6, 6), tw_f=rng.uniform(0.6, 1.5), tw_p=rng.uniform(0, TAU),
                          col=col, kind=('spark' if rng.random() < 0.18 else 'star'), curl=rng.uniform(-60, 60)))
    return stars


STARS = _make_stars()


def _bez(P0, P1, P2, P3, u):
    a = (1 - u) ** 3
    b = 3 * (1 - u) ** 2 * u
    c = 3 * (1 - u) * u * u
    d = u ** 3
    return (a * P0[0] + b * P1[0] + c * P2[0] + d * P3[0], a * P0[1] + b * P1[1] + c * P2[1] + d * P3[1])


def star_pos(s, t):
    u = seg(t, s['s0'], s['s0'] + s['d'])
    uu = e_o2(u) * 0.35 + e_io(u) * 0.65
    x, y = _bez(s['M'], s['P1'], s['P2'], s['E'], uu)
    # curl sideways mid-flight
    x += s['curl'] * math.sin(math.pi * uu) * math.sin(uu * 5)
    return x, y, u


# ---------------------------------------------------------------- night
def night_amount(t):
    return e_io(seg(t, 15.6, 17.1))


CAM = Track((0, (1.12, 250, 1330)), (1.0, (1.12, 250, 1330)), (4.6, (1.0, 540, 1150)),
            (11.3, (1.0, 540, 1150)), (13.25, (1.06, 560, 1180)), (14.1, (1.14, 640, 1420)), (15.15, (1.14, 640, 1420)),
            (16.4, (1.0, 540, 1150)), (17.25, (1.0, 540, 1150)), (18.6, (1.26, 575, 1390)),
            (20.0, (1.3, 575, 1390), 'o'))


def camera(t):
    import cairo
    z, fx, fy = CAM(t)
    m = cairo.Matrix()
    m.translate(fx, fy)
    m.scale(z, z)
    m.translate(-fx, -fy)
    return m

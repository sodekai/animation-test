"""Side-view fighter rig: keyframed world-space targets -> IK skeleton -> cel/silhouette drawing."""
import math
import cairo
from core import *

G = 1480.0                      # ground line (feet)
TH, SHN = 90.0, 88.0            # thigh, shin
UA, FA = 64.0, 58.0             # upper arm, forearm
SPINE = 118.0
HEAD_R = 21.0
BLADE = 178.0


# ------------------------------------------------------------------ vectors
def vadd(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k)


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vlen(a):
    return math.hypot(a[0], a[1])


def vnorm(a):
    l = vlen(a) or 1.0
    return (a[0] / l, a[1] / l)


def adir(deg):
    """Screen direction for a math-style angle (0 = right, 90 = up)."""
    r = math.radians(deg)
    return (math.cos(r), -math.sin(r))


def perp(d):
    return (-d[1], d[0])


def ik2(A, T, l1, l2, prefer):
    d = vsub(T, A)
    dist = vlen(d)
    dd = clamp(dist, abs(l1 - l2) + 1, l1 + l2 - 0.5)
    a = math.atan2(d[1], d[0])
    cg = (l1 * l1 + dd * dd - l2 * l2) / (2 * l1 * dd)
    g = math.acos(clamp(cg, -1, 1))
    m1 = (A[0] + l1 * math.cos(a + g), A[1] + l1 * math.sin(a + g))
    m2 = (A[0] + l1 * math.cos(a - g), A[1] + l1 * math.sin(a - g))
    M = prefer(m1, m2)
    e = vnorm(vsub(T, M))
    return M, (M[0] + e[0] * l2, M[1] + e[1] * l2)


# ------------------------------------------------------------------ keyframes
def WP(x, y):
    return ('w', x, y)


def AT(x, y):
    return ('at', x, y)


def pose(hip, f, lean=5, head=0, fN=(30, 0), fF=(-34, 0), hN=(30, -20), hF=(14, -8), sN=20, sF=150, grip=False, raw=False):
    """Local offsets are in the fighter's facing frame (x forward, y down, relative to hip; feet: (dx, height)).
    W(x, y) gives an absolute world point, AT(x, y) aims a sword at a world point. Everything is stored in world space."""
    def tw(p, foot=False):
        if isinstance(p[0], str):
            return (float(p[1]), float(p[2]))
        if foot:
            return (hip[0] + f * p[0], G - p[1])
        return (hip[0] + f * p[0], hip[1] + p[1])

    def ta(a, hand):
        if isinstance(a, tuple):
            return math.degrees(math.atan2(-(a[2] - hand[1]), a[1] - hand[0]))
        return a if f > 0 else 180 - a
    hNw = tw(hN)
    sNw = ta(sN, hNw)
    if grip:
        d = adir(sNw)
        hFw = (hNw[0] - d[0] * 20, hNw[1] - d[1] * 20)
    else:
        hFw = tw(hF)
    return dict(hip=(float(hip[0]), float(hip[1])), f=f, lean=float(lean), head=float(head), fN=tw(fN, True),
                fF=tw(fF, True), hN=hNw, hF=hFw, sN=sNw, sF=ta(sF, hFw), raw=raw)


class Choreo:
    FIELDS = ('hip', 'lean', 'head', 'fN', 'fF', 'hN', 'hF', 'sN', 'sF')

    def __init__(self, keys, holds=()):
        # keys: (t, pose[, ease])
        self.keys = [(k[0], dict(k[1]), k[2] if len(k) > 2 else 'io') for k in keys]
        # unwrap sword angles so interpolation takes the short way unless a key is marked raw
        for i in range(1, len(self.keys)):
            prev, cur = self.keys[i - 1][1], self.keys[i][1]
            if cur.get('raw'):
                continue
            for s in ('sN', 'sF'):
                while cur[s] - prev[s] > 180:
                    cur[s] -= 360
                while cur[s] - prev[s] < -180:
                    cur[s] += 360
        self.holds = holds

    def warp(self, t):
        for tc, d in self.holds:
            if tc <= t < tc + d:
                return tc
        return t

    def __call__(self, t):
        t = self.warp(t)
        k = self.keys
        if t <= k[0][0]:
            return dict(k[0][1])
        for i in range(1, len(k)):
            if t < k[i][0]:
                t0, p0, _ = k[i - 1]
                t1, p1, e = k[i]
                w = EASES[e]((t - t0) / (t1 - t0))
                out = {}
                for fld in self.FIELDS:
                    out[fld] = lerpv(p0[fld], p1[fld], w)
                out['f'] = p0['f'] if w < 0.5 else p1['f']
                return out
        return dict(k[-1][1])


# ------------------------------------------------------------------ skeleton
def solve(p):
    f = p['f']
    lam = math.radians(p['lean'])
    hip = p['hip']
    u = (f * math.sin(lam), -math.cos(lam))
    nf = (f * math.cos(lam), math.sin(lam))
    chest = vadd(hip, u, SPINE)
    ha = lam + math.radians(p['head'])
    uh = (f * math.sin(ha), -math.cos(ha))
    nfh = (f * math.cos(ha), math.sin(ha))
    neck = vadd(chest, u, 6)
    head = vadd(neck, uh, 13 + HEAD_R)
    shN = vadd(vadd(chest, u, -12), nf, -3)
    shF = vadd(vadd(chest, u, -10), nf, 5)
    hipN = vadd(vadd(hip, nf, -5), u, 4)
    hipF = vadd(vadd(hip, nf, 5), u, 2)

    def low(a, b):
        return a if a[1] > b[1] else b

    def fwd(a, b):
        return a if (a[0] - b[0]) * f > 0 else b
    elN, haN = ik2(shN, p['hN'], UA, FA, low)
    elF, haF = ik2(shF, p['hF'], UA, FA, low)
    knN, anN = ik2(hipN, p['fN'], TH, SHN, fwd)
    knF, anF = ik2(hipF, p['fF'], TH, SHN, fwd)
    return dict(f=f, hip=hip, u=u, nf=nf, chest=chest, neck=neck, head=head, uh=uh, nfh=nfh,
                shN=shN, shF=shF, elN=elN, elF=elF, haN=haN, haF=haF,
                hipN=hipN, hipF=hipF, knN=knN, knF=knF, anN=anN, anF=anF,
                waist=vadd(hip, u, 22), sN=p['sN'], sF=p['sF'])


def hair_anchor(J):
    return vadd(vadd(J['head'], J['uh'], 15), J['nfh'], -13)


def sash_anchor(J, k=0):
    return vadd(vadd(J['waist'], J['nf'], -21), J['u'], -3 * k)


def blade_points(hand, ang, curve=7.0, length=BLADE):
    d = adir(ang)
    n = perp(d)
    base = vadd(hand, d, 13)
    tip = vadd(hand, d, 13 + length)
    return base, tip, d, n


# ------------------------------------------------------------------ styles
YASUO = dict(name='yasuo', skin=hexc('#3e2c2b'), hair=hexc('#140f17'), top=hexc('#243a5e'), top_d=hexc('#182844'),
             hak=hexc('#1c2539'), hak_d=hexc('#121827'), sash=hexc('#3f80c8'), sash_d=hexc('#2c5f9c'),
             accent=hexc('#7fd0ff'), pauldron=hexc('#3a4353'), scab=hexc('#17131b'), handle=hexc('#2b2331'),
             tsuba=hexc('#b89a5a'), foot=hexc('#120e14'))
YONE = dict(name='yone', skin=hexc('#382a2c'), hair=hexc('#0e0a10'), top=hexc('#2c1b26'), top_d=hexc('#1d1219'),
            hak=hexc('#1e1519'), hak_d=hexc('#140d11'), sash=hexc('#b3242f'), sash_d=hexc('#7f1920'),
            accent=hexc('#ff4050'), mask=hexc('#c4202f'), mask_d=hexc('#7d1520'), horn=hexc('#2a0e14'),
            scab=hexc('#160f14'), handle=hexc('#2c1d24'), tsuba=hexc('#9a2a30'), foot=hexc('#0f0a0d'))
BLADES = {
    'yasuo': [dict(core=hexc('#f2f8ff'), glow=hexc('#6fd2ff'))],
    'yone': [dict(core=hexc('#ffe1e1'), glow=hexc('#ff2a40')), dict(core=hexc('#e6f3ff'), glow=hexc('#4aa6ff'))],
}


# ------------------------------------------------------------------ drawing helpers
def fillc(c, col, a=1.0):
    if len(col) == 4:
        c.set_source_rgba(*col)
    else:
        c.set_source_rgba(*col, a)
    c.fill()


def poly(c, pts, close=True):
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    if close:
        c.close_path()


def smooth_poly(c, pts):
    """Closed Catmull-Rom style smooth outline."""
    n = len(pts)
    mids = [((pts[i][0] + pts[(i + 1) % n][0]) / 2, (pts[i][1] + pts[(i + 1) % n][1]) / 2) for i in range(n)]
    c.move_to(*mids[-1])
    for i in range(n):
        c.curve_to(pts[i][0], pts[i][1], pts[i][0], pts[i][1], mids[i][0], mids[i][1])
    c.close_path()


def capsule(c, A, B, rA, rB):
    ang = math.atan2(B[1] - A[1], B[0] - A[0])
    c.new_sub_path()
    c.arc(B[0], B[1], rB, ang - math.pi / 2, ang + math.pi / 2)
    c.arc(A[0], A[1], rA, ang + math.pi / 2, ang + 3 * math.pi / 2)
    c.close_path()


def ribbon(c, pts, w0, w1, jag=0.0, seed=0):
    """Tapered ribbon along a polyline (for hair / sashes)."""
    n = len(pts)
    left, right = [], []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        d = vnorm(vsub(b, a))
        nn = perp(d)
        k = i / (n - 1)
        w = lerp(w0, w1, k)
        j = jag * (1 if (i + seed) % 2 else -0.4) * (1 - k * 0.5)
        left.append(vadd(p, nn, w + j))
        right.append(vadd(p, nn, -w + j * 0.6))
    smooth_poly(c, left + right[::-1])


def hakama_leg(c, hipj, knee, ankle, col, f):
    d1 = vnorm(vsub(knee, hipj))
    d2 = vnorm(vsub(ankle, knee))
    n1, n2 = perp(d1), perp(d2)
    nk = vnorm(vadd(n1, n2))
    pts = [vadd(hipj, n1, 19), vadd(knee, nk, 21), vadd(ankle, n2, 29), vadd(vadd(ankle, n2, 20), d2, 8),
           vadd(vadd(ankle, n2, -18), d2, 8), vadd(ankle, n2, -28), vadd(knee, nk, -20), vadd(hipj, n1, -18)]
    smooth_poly(c, pts)
    fillc(c, col)


def foot(c, ankle, f, col):
    pts = [vadd(ankle, (-f * 8, -4)), vadd(ankle, (f * 26, 3)), vadd(ankle, (f * 24, 9)), vadd(ankle, (-f * 10, 9))]
    smooth_poly(c, pts)
    fillc(c, col)


def torso(c, J, st):
    hip, u, nf = J['hip'], J['u'], J['nf']
    prof = [(0, 25, 0), (30, 21, 1), (62, 25, 5), (96, 29, 6), (118, 22, 2)]
    left = [vadd(vadd(hip, u, s), nf, w + fw) for s, w, fw in prof]
    right = [vadd(vadd(hip, u, s), nf, -w + fw * 0.3) for s, w, fw in prof]
    smooth_poly(c, left + right[::-1])
    fillc(c, st['top'])
    # collar / lapel line
    c.move_to(*vadd(vadd(hip, u, 112), nf, 14))
    c.line_to(*vadd(vadd(hip, u, 34), nf, 20))
    c.set_source_rgba(*st['accent'], 0.55)
    c.set_line_width(2.5)
    c.stroke()


def sash_band(c, J, st):
    w = J['waist']
    u, nf = J['u'], J['nf']
    pts = [vadd(vadd(w, nf, 24), u, 7), vadd(vadd(w, nf, 24), u, -7), vadd(vadd(w, nf, -23), u, -7), vadd(vadd(w, nf, -23), u, 7)]
    poly(c, pts)
    fillc(c, st['sash'])


def arm(c, sh, el, ha, col, width=9.5, fore=8.0):
    capsule(c, sh, el, width, width * 0.9)
    fillc(c, col)
    capsule(c, el, ha, width * 0.9, fore)
    fillc(c, col)


def sleeve(c, sh, el, ha, col, sway=0.0):
    down = (sway * 0.4, 1.0)
    mid = vadd(el, vsub(ha, el), 0.55)
    pts = [vadd(sh, (0, -8)), el, mid, vadd(vadd(mid, down, 30), (sway * 10, 0)), vadd(el, down, 30), vadd(sh, down, 16)]
    smooth_poly(c, pts)
    fillc(c, col)


def hand(c, p, col, r=8.5):
    c.arc(p[0], p[1], r, 0, TAU)
    fillc(c, col)


def head_profile(c, J, st):
    h, uh, nf = J['head'], J['uh'], J['nfh']
    # neck
    capsule(c, J['neck'], vadd(h, uh, -10), 9, 9)
    fillc(c, st['skin'])
    c.new_sub_path()
    c.arc(h[0], h[1], HEAD_R, 0, TAU)
    fillc(c, st['skin'])
    face = [vadd(vadd(h, nf, 10), uh, 13), vadd(vadd(h, nf, 24), uh, 1), vadd(vadd(h, nf, 21), uh, -5),
            vadd(vadd(h, nf, 20), uh, -10), vadd(vadd(h, nf, 15), uh, -21), vadd(vadd(h, nf, 2), uh, -20),
            vadd(h, nf, -6)]
    poly(c, face)
    fillc(c, st['skin'])


def yasuo_hair_cap(c, J, st):
    h, uh, nf = J['head'], J['uh'], J['nfh']
    pts = [vadd(vadd(h, nf, 16), uh, 12), vadd(vadd(h, nf, 25), uh, 6), vadd(vadd(h, nf, 12), uh, 2),
           vadd(vadd(h, nf, 18), uh, -6), vadd(vadd(h, nf, 4), uh, 2), vadd(vadd(h, nf, 2), uh, -8),
           vadd(vadd(h, nf, -10), uh, -6), vadd(vadd(h, nf, -20), uh, -14), vadd(vadd(h, nf, -24), uh, 2),
           vadd(vadd(h, nf, -20), uh, 16), vadd(vadd(h, nf, -6), uh, 25), vadd(vadd(h, nf, 8), uh, 24)]
    poly(c, pts)
    fillc(c, st['hair'])


def yone_hair_cap(c, J, st):
    h, uh, nf = J['head'], J['uh'], J['nfh']
    pts = [vadd(vadd(h, nf, 12), uh, 16), vadd(vadd(h, nf, 18), uh, 8), vadd(vadd(h, nf, 4), uh, 8),
           vadd(vadd(h, nf, -8), uh, -2), vadd(vadd(h, nf, -18), uh, -18), vadd(vadd(h, nf, -24), uh, 0),
           vadd(vadd(h, nf, -18), uh, 17), vadd(vadd(h, nf, -2), uh, 24)]
    smooth_poly(c, pts)
    fillc(c, st['hair'])


def yone_mask(c, J, st, eye=1.0):
    h, uh, nf = J['head'], J['uh'], J['nfh']
    # horns sweeping back
    for k, (sx, col) in enumerate(((0, st['horn']), (-7, shade(st['horn'], 0.8)))):
        b0 = vadd(vadd(h, nf, 8 + sx), uh, 14)
        b1 = vadd(vadd(h, nf, -2 + sx), uh, 18)
        tip = vadd(vadd(h, nf, -26 + sx), uh, 50 - k * 4)
        ctrl = vadd(vadd(h, nf, 10 + sx), uh, 44)
        c.move_to(*b0)
        c.curve_to(*ctrl, *ctrl, *tip)
        c.curve_to(*vadd(ctrl, nf, -6), *vadd(ctrl, nf, -8), *b1)
        c.close_path()
        fillc(c, col)
    pts = [vadd(vadd(h, nf, 4), uh, 15), vadd(vadd(h, nf, 22), uh, 8), vadd(vadd(h, nf, 26), uh, 0),
           vadd(vadd(h, nf, 22), uh, -9), vadd(vadd(h, nf, 18), uh, -20), vadd(vadd(h, nf, 6), uh, -18),
           vadd(vadd(h, nf, 2), uh, -4)]
    smooth_poly(c, pts)
    fillc(c, st['mask'])
    # fangs / mouth line
    c.move_to(*vadd(vadd(h, nf, 21), uh, -10))
    c.line_to(*vadd(vadd(h, nf, 9), uh, -12))
    c.set_source_rgba(*st['mask_d'], 1)
    c.set_line_width(2.4)
    c.stroke()
    # eye slit (the bright part is re-drawn in the FX layer)
    e0, e1 = vadd(vadd(h, nf, 8), uh, 4), vadd(vadd(h, nf, 21), uh, 2)
    c.move_to(*e0)
    c.line_to(*e1)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgba(0.1, 0.0, 0.02, 1)
    c.set_line_width(4.5)
    c.stroke()
    return (e0, e1)


def pauldron(c, J, st):
    sh, el = J['shN'], J['elN']
    d = vnorm(vsub(el, sh))
    n = perp(d)
    ctr = vadd(vadd(sh, d, 10), n, -J['f'] * 2)
    ang = math.atan2(d[1], d[0])
    c.save()
    c.translate(*ctr)
    c.rotate(ang)
    for k, (r, col) in enumerate(((27, st['pauldron']), (20, shade(st['pauldron'], 0.8)))):
        c.new_sub_path()
        c.arc(-4 + k * 3, 0, r, -math.pi / 2 - 1.5, -math.pi / 2 + 1.5)
        c.arc_negative(-4 + k * 3, 6, r * 0.55, -math.pi / 2 + 1.2, -math.pi / 2 - 1.2)
        c.close_path()
        fillc(c, col)
    c.restore()
    # big round shoulder plate
    c.save()
    c.translate(*vadd(sh, d, 4))
    c.rotate(ang)
    c.scale(1.25, 1.0)
    c.arc(0, 0, 17, 0, TAU)
    c.restore()
    fillc(c, st['pauldron'])
    c.save()
    c.translate(*vadd(sh, d, 4))
    c.rotate(ang)
    c.scale(1.25, 1.0)
    c.arc(0, 0, 17, math.pi * 1.1, math.pi * 1.9)
    c.restore()
    c.set_source_rgba(*st['accent'], 0.45)
    c.set_line_width(2)
    c.stroke()


def handle(c, hand_p, ang, st):
    d = adir(ang)
    n = perp(d)
    a, b = vadd(hand_p, d, -30), vadd(hand_p, d, 9)
    capsule(c, a, b, 4.5, 4.5)
    fillc(c, st['handle'])
    t = vadd(hand_p, d, 12)
    poly(c, [vadd(vadd(t, n, 10), d, -2), vadd(vadd(t, n, 10), d, 2), vadd(vadd(t, n, -10), d, 2), vadd(vadd(t, n, -10), d, -2)])
    fillc(c, st['tsuba'])


def scabbard(c, J, st, k, sheathed):
    w = J['waist']
    nf, u, f = J['nf'], J['u'], J['f']
    mouth = vadd(vadd(w, nf, 12 - k * 5), u, -2 - k * 6)
    d = vnorm((-nf[0] * 0.8 - u[0] * 0.62, -nf[1] * 0.8 - u[1] * 0.62))
    end = vadd(mouth, d, 128)
    capsule(c, mouth, end, 5, 4)
    fillc(c, st['scab'])
    if sheathed:
        hd = (-d[0], -d[1])
        ang = math.degrees(math.atan2(-hd[1], hd[0]))
        hp = vadd(mouth, hd, 4)
        handle(c, vadd(hp, hd, 26), ang, st)


def draw_fighter(c, J, st, chains, drawn, alpha_eye=1.0):
    """Draws the fighter into c. drawn: list of bools per sword (near, far). Returns eye slit (Yone) for FX."""
    f = J['f']
    yone = st['name'] == 'yone'
    # behind: coat tail / sash tails / ponytail
    if 'coat' in chains:
        ribbon(c, chains['coat'], 14, 7)
        fillc(c, st['top_d'])
        ribbon(c, chains['coat'], 5, 3)
        fillc(c, st['sash_d'])
    for k in ('sash0', 'sash1'):
        if k in chains:
            ribbon(c, chains[k], 6, 3)
            fillc(c, st['sash_d'] if k == 'sash1' else st['sash'])
    if 'hair' in chains:
        pts = [hair_anchor(J)] + list(chains['hair'][1:])
        if yone:
            ribbon(c, pts, 10, 3)
        else:
            ribbon(c, pts, 16, 4, jag=5, seed=1)
        fillc(c, st['hair'])
    # far limbs
    hakama_leg(c, J['hipF'], J['knF'], J['anF'], st['hak_d'], f)
    foot(c, J['anF'], f, st['foot'])
    sleeve(c, J['shF'], J['elF'], J['haF'], st['top_d'], sway=0.3 * f)
    arm(c, J['shF'], J['elF'], J['haF'], st['top_d'])
    hand(c, J['haF'], shade(st['skin'], 0.85))
    if len(drawn) > 1 and drawn[1]:
        handle(c, J['haF'], J['sF'], st)
    # body
    torso(c, J, st)
    hakama_leg(c, J['hipN'], J['knN'], J['anN'], st['hak'], f)
    foot(c, J['anN'], f, st['foot'])
    sash_band(c, J, st)
    nscab = 2 if yone else 1
    for k in range(nscab):
        sheathed = not drawn[k]
        scabbard(c, J, st, k, sheathed)
    hc = J['head']
    c.save()
    c.translate(*hc)
    c.scale(1.13, 1.13)
    c.translate(-hc[0], -hc[1])
    head_profile(c, J, st)
    eye = None
    if yone:
        yone_hair_cap(c, J, st)
        eye = yone_mask(c, J, st)
        eye = tuple(c.user_to_device(*p) for p in eye)
    else:
        yasuo_hair_cap(c, J, st)
    c.restore()
    if eye:
        eye = tuple(c.device_to_user(*p) for p in eye)
    # near arm
    if yone:
        sleeve(c, J['shN'], J['elN'], J['haN'], st['top'], sway=0.3 * f)
        arm(c, J['shN'], J['elN'], J['haN'], st['top'])
    else:
        arm(c, J['shN'], J['elN'], J['haN'], st['skin'], width=9.0)
        # wrist wrap
        d = vnorm(vsub(J['haN'], J['elN']))
        capsule(c, vadd(J['haN'], d, -20), vadd(J['haN'], d, -8), 8.5, 8)
        fillc(c, st['sash_d'])
        pauldron(c, J, st)
    hand(c, J['haN'], st['skin'])
    if drawn[0]:
        handle(c, J['haN'], J['sN'], st)
    return eye


def draw_blade(c, hand_p, ang, bl, alpha=1.0, glow_w=15):
    base, tip, d, n = blade_points(hand_p, ang)
    mid = vadd(vadd(base, d, BLADE * 0.5), n, 5)
    # soft coloured halo under the blade so the bloom picks up the tint
    c.move_to(*base)
    c.curve_to(*mid, *mid, *tip)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgba(*bl['glow'], 0.45 * alpha)
    c.set_line_width(glow_w)
    c.stroke()
    # blade body (edge + spine)
    spine_mid = vadd(mid, n, 5)
    c.move_to(*vadd(base, n, 3.5))
    c.curve_to(*spine_mid, *spine_mid, *tip)
    c.curve_to(*vadd(mid, n, -1), *vadd(mid, n, -1), *vadd(base, n, -3))
    c.close_path()
    c.set_source_rgba(*bl['core'], alpha)
    c.fill()
    return base, tip

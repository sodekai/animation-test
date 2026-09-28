"""The duel: keyframes, events, wind, and the hair/cloth simulation."""
import math
import numpy as np
from core import *
from rig import *

# ---------------------------------------------------------------- events
# clashes: (time, x, y, power)
CLASHES = [(5.0, 540, 1180, 1.0), (6.1, 520, 1120, 0.65), (6.95, 575, 1158, 0.9), (7.45, 565, 1150, 0.7),
           (10.55, 380, 1150, 0.85)]
HOLDS = [(5.0, 0.1), (6.1, 0.05), (6.95, 0.08), (7.45, 0.06), (10.55, 0.07)]
PASS_T0, PASS_T1, PASS_X = 13.12, 13.3, 13.21
SHEATH_T = 16.35
XSLASH_T = 16.45
TORNADO_T0, TORNADO_CUT = 9.25, 10.02
SPIRIT_T0, SPIRIT_T1 = 10.2, 11.05
YONE_IN = (0.35, 1.9)
YONE_OUT = (18.0, 19.4)

P1 = (540, 1180)
P2 = (520, 1120)
P3 = (575, 1158)
P4 = (565, 1150)
P5 = (380, 1150)

# ---------------------------------------------------------------- Yasuo
YAS = Choreo([
    (0.0, pose((290, 1312), 1, 4, -2, (26, 0), (-30, 0), (30, -18), (12, -6), 20)),
    (2.6, pose((290, 1316), 1, 6, -4, (26, 0), (-30, 0), (30, -18), (12, -6), 20)),
    (3.3, pose((286, 1326), 1, 10, -2, WP(312, G), WP(256, G), (34, -16), (18, -8), 20)),
    (3.55, pose((292, 1320), 1, 6, -6, WP(332, G), WP(244, G), (86, -96), (8, -30), 72), 'o'),
    (3.95, pose((295, 1332), 1, 12, -4, WP(349, G), WP(233, G), (58, -58), (44, -50), 34, grip=True)),
    (4.35, pose((272, 1342), 1, -2, 2, WP(349, G), WP(233, G), (30, -62), (16, -52), 62, grip=True)),
    (4.7, pose((372, 1318), 1, 28, -6, (30, 40), (-92, 30), (62, -48), (48, -44), 22, grip=True), 'i2'),
    (5.0, pose((445, 1338), 1, 20, -4, WP(528, G), WP(352, G), WP(505, 1218), None, AT(*P1), grip=True), 'o'),
    (5.5, pose((452, 1335), 1, 24, -6, WP(528, G), WP(352, G), WP(510, 1212), None, AT(542, 1172), grip=True)),
    (5.75, pose((400, 1330), 1, 6, -2, WP(478, G), WP(335, G), (58, -70), None, 55, grip=True)),
    (6.1, pose((410, 1334), 1, 4, -8, WP(478, G), WP(335, G), WP(452, 1172), None, AT(*P2), grip=True), 'o'),
    (6.3, pose((414, 1352), 1, 10, 0, WP(478, G), WP(335, G), (40, -70), None, 72, grip=True)),
    (6.55, pose((442, 1188), 1, 6, -6, (34, 72), (-30, 62), (22, -112), None, 102, grip=True), 'o'),
    (6.95, pose((470, 1296), 1, 22, 4, (40, 26), (-40, 34), WP(505, 1140), None, AT(*P3), grip=True), 'i2'),
    (7.08, pose((470, 1338), 1, 18, 2, WP(525, G), WP(410, G), WP(510, 1150), None, -10, grip=True), 'o'),
    (7.22, pose((452, 1344), 1, -6, 0, WP(525, G), WP(400, G), (-30, -32), None, 200, grip=True)),
    (7.45, dict(pose((470, 1330), 1, 16, -4, WP(525, G), WP(400, G), WP(520, 1190), None, AT(*P4), grip=True),
                sN=401.6, raw=True), 'o'),
    (7.58, pose((474, 1330), 1, 12, -6, WP(525, G), WP(400, G), (62, -92), None, 60, grip=True)),
    (7.72, pose((440, 1304), 1, -10, 0, WP(505, G), WP(390, G), (50, -80), None, 70, grip=True)),
    (7.96, pose((360, 1222), 1, -14, 4, (22, 52), (-22, 42), (44, -62), None, 40, grip=True), 'o2'),
    (8.2, pose((285, 1348), 1, 8, 0, WP(345, G), WP(220, G), (50, -52), None, 25, grip=True), 'i2'),
    (8.6, pose((280, 1340), 1, 2, -2, WP(350, G), WP(210, G), (-6, -62), None, 2, grip=True)),
    (9.12, pose((278, 1343), 1, 0, -2, WP(350, G), WP(210, G), (-12, -62), None, 1, grip=True)),
    (9.27, pose((312, 1336), 1, 20, -4, WP(382, G), WP(222, G), (104, -62), (40, -40), -2), 'o'),
    (9.6, pose((302, 1334), 1, 10, -2, WP(382, G), WP(222, G), (60, -62), None, 30, grip=True)),
    (10.3, pose((300, 1336), 1, 8, -2, WP(372, G), WP(228, G), (56, -66), None, 38, grip=True)),
    (10.45, pose((292, 1338), 1, 4, -6, WP(372, G), WP(228, G), (50, -84), None, 62, grip=True)),
    (10.55, pose((286, 1340), 1, 0, -8, WP(372, G), WP(228, G), WP(336, 1196), None, AT(*P5), grip=True), 'o'),
    (10.8, pose((270, 1336), 1, -4, 0, WP(350, G), WP(218, G), (50, -70), None, 55, grip=True)),
    (11.4, pose((300, 1346), 1, 14, -4, WP(376, G), WP(214, G), (-12, -46), None, 200, grip=True)),
    (13.05, pose((302, 1348), 1, 16, -4, WP(376, G), WP(214, G), (-14, -46), None, 202, grip=True)),
    (13.12, pose((332, 1352), 1, 30, -6, WP(390, G), WP(230, G), (-20, -40), None, 205, grip=True), 'i2'),
    (13.3, pose((740, 1354), 1, 30, 0, WP(820, G), WP(630, G), (96, -38), (-40, -50), -25), 'o'),
    (15.0, pose((740, 1350), 1, 26, 0, WP(820, G), WP(630, G), (96, -40), (-40, -50), -24)),
    (15.8, pose((740, 1318), 1, 6, 0, WP(792, G), WP(698, G), (70, -62), (-10, -40), 12)),
    (16.2, pose((740, 1314), 1, 4, -2, WP(770, G), WP(708, G), (40, -30), (14, -8), 200)),
    (16.5, pose((740, 1312), 1, 4, -2, WP(768, G), WP(710, G), (30, -18), (12, -6), 200)),
    (18.8, pose((740, 1312), 1, 4, -2, WP(768, G), WP(710, G), (30, -18), (12, -6), 200)),
    (19.05, pose((736, 1314), -1, 4, 2, WP(710, G), WP(768, G), (26, -16), (12, -6), 20)),
    (19.6, pose((736, 1316), -1, 6, 16, WP(710, G), WP(768, G), (26, -16), (12, -6), 20)),
    (20.0, pose((736, 1316), -1, 6, 18, WP(710, G), WP(768, G), (26, -16), (12, -6), 20)),
], holds=HOLDS)

# ---------------------------------------------------------------- Yone
YON = Choreo([
    (0.0, pose((790, 1312), -1, 3, 0, (26, 0), (-30, 0), (26, -14), (20, -10), 20, 20)),
    (2.6, pose((790, 1314), -1, 5, -2, (26, 0), (-30, 0), (26, -14), (20, -10), 20, 20)),
    (3.35, pose((792, 1322), -1, 8, 0, WP(766, G), WP(822, G), (30, -18), (26, -22), 20, 20)),
    (3.6, pose((790, 1318), -1, 6, -6, WP(752, G), WP(830, G), (84, -90), (-40, -62), 76, 150), 'o'),
    (4.0, pose((788, 1334), -1, 10, -4, WP(736, G), WP(850, G), (60, -50), (30, -86), 20, 72)),
    (4.35, pose((810, 1342), -1, -2, 2, WP(736, G), WP(870, G), (34, -56), (10, -90), 40, 95)),
    (4.7, pose((715, 1318), -1, 28, -6, (30, 40), (-90, 30), (62, -48), (42, -62), 15, 40), 'i2'),
    (5.0, pose((635, 1338), -1, 18, -4, WP(560, G), WP(720, G), WP(578, 1205), WP(592, 1166), AT(*P1), AT(*P1)), 'o'),
    (5.5, pose((628, 1335), -1, 22, -6, WP(560, G), WP(720, G), WP(572, 1200), WP(588, 1162), AT(540, 1172), AT(540, 1172))),
    (5.75, pose((690, 1330), -1, 6, -2, WP(620, G), WP(760, G), (50, -60), (30, -92), 40, 95)),
    (5.92, pose((672, 1328), -1, 0, -4, WP(620, G), WP(760, G), (10, -132), (40, -50), 112, 20)),
    (6.1, pose((640, 1336), -1, 18, 2, WP(575, G), WP(705, G), WP(600, 1150), (30, -40), AT(*P2), 0), 'i2'),
    (6.3, pose((650, 1350), -1, 22, 0, WP(575, G), WP(705, G), (40, -80), (-24, -20), 60, 190)),
    (6.45, pose((640, 1356), -1, 26, 0, WP(575, G), WP(705, G), (40, -86), (62, 28), 60, -12), 'o'),
    (6.64, pose((645, 1345), -1, 4, -8, WP(590, G), WP(700, G), WP(610, 1210), WP(560, 1212), AT(*P3), AT(*P3))),
    (6.95, pose((648, 1352), -1, 2, -10, WP(590, G), WP(700, G), WP(612, 1214), WP(560, 1216), AT(*P3), AT(*P3))),
    (7.2, pose((642, 1340), -1, 8, -4, WP(590, G), WP(700, G), WP(598, 1186), (20, -40), AT(*P4), 30)),
    (7.45, pose((650, 1340), -1, 10, -6, WP(590, G), WP(700, G), WP(605, 1195), (20, -40), AT(*P4), 30), 'o'),
    (7.7, pose((670, 1336), -1, -6, 0, WP(610, G), WP(730, G), (40, -80), (20, -70), 60, 60)),
    (8.1, pose((800, 1344), -1, 10, -2, WP(730, G), WP(862, G), (60, -50), (30, -84), 20, 76), 'o'),
    (9.6, pose((800, 1346), -1, 10, -4, WP(730, G), WP(862, G), (60, -52), (30, -86), 20, 76)),
    (9.8, pose((798, 1340), -1, -4, 4, WP(730, G), WP(862, G), (20, -122), (40, -116), 120, 72)),
    (10.0, pose((780, 1346), -1, 22, -2, WP(720, G), WP(860, G), (90, -22), (78, -44), -40, -72), 'o'),
    (11.05, pose((780, 1346), -1, 22, -2, WP(720, G), WP(860, G), (90, -22), (78, -44), -40, -72)),
    (11.4, pose((780, 1348), -1, 14, -4, WP(706, G), WP(866, G), (40, -40), (-12, -60), -10, 200)),
    (13.05, pose((780, 1350), -1, 16, -4, WP(706, G), WP(866, G), (40, -42), (-14, -60), -12, 202)),
    (13.12, pose((750, 1352), -1, 30, -6, WP(690, G), WP(850, G), (46, -40), (-20, -54), -14, 205), 'i2'),
    (13.3, pose((340, 1354), -1, 30, 0, WP(260, G), WP(440, G), (96, -40), (-60, -50), -25, 190), 'o'),
    (15.0, pose((340, 1350), -1, 26, 0, WP(260, G), WP(440, G), (96, -42), (-60, -52), -24, 190)),
    (15.8, pose((340, 1318), -1, 6, 0, WP(290, G), WP(382, G), (70, -62), (-20, -60), 12, 170)),
    (16.2, pose((340, 1314), -1, 4, -2, WP(312, G), WP(372, G), (32, -24), (24, -20), 200, 200)),
    (16.5, pose((340, 1312), -1, 4, -2, WP(314, G), WP(370, G), (26, -14), (20, -10), 200, 200)),
    (17.4, pose((340, 1312), -1, 4, -2, WP(314, G), WP(370, G), (26, -14), (20, -10), 200, 200)),
    (17.65, pose((344, 1314), 1, 4, 4, WP(370, G), WP(314, G), (26, -14), (20, -10), 20, 20)),
    (20.0, pose((344, 1314), 1, 4, 6, WP(370, G), WP(314, G), (26, -14), (20, -10), 20, 20)),
], holds=HOLDS)

# ---------------------------------------------------------------- Yone's spirit (Soul Unbound)
SPI = Choreo([
    (SPIRIT_T0, YON.keys[22][1]),
    (10.33, pose((752, 1334), -1, 30, -6, WP(700, G), WP(830, G), (60, -60), (40, -70), 30, 60)),
    (10.55, pose((440, 1330), -1, 26, -4, WP(390, G), WP(520, G), WP(412, 1188), (20, -60), AT(*P5), 40), 'o'),
    (10.75, pose((478, 1322), -1, -10, 0, WP(420, G), WP(540, G), (50, -80), (20, -70), 60, 60)),
    (11.02, YON.keys[23][1], 'i2'),
], holds=HOLDS)


def drawn_yasuo(t):
    return [3.47 <= t < SHEATH_T]


def drawn_yone(t):
    d = 3.52 <= t < SHEATH_T - 0.03
    return [d, d]


def yone_alpha(t):
    a = e_io(seg(t, YONE_IN[0], YONE_IN[1]))
    return a


def spirit_alpha(t):
    if not (SPIRIT_T0 <= t < SPIRIT_T1):
        return 0.0
    return e_o(seg(t, SPIRIT_T0, SPIRIT_T0 + 0.12)) * (1 - e_i(seg(t, SPIRIT_T1 - 0.1, SPIRIT_T1)))


# ---------------------------------------------------------------- wind
WIND = Track((0, 70), (3.3, 70), (3.55, 420, 'o'), (4.3, 110), (8.6, 110), (9.2, 160), (9.4, 360), (10.2, 300),
             (10.6, 120), (11.4, 40), (13.0, 25), (13.22, 520, 'o'), (13.8, 30), (16.4, 30), (16.55, 480, 'o'),
             (17.3, 60), (18.0, 25), (20, 20))
TURB = 1.0


def wind(t):
    return WIND(t)


# petal time warp: slow motion for the standoff and the frozen aftermath
def _speed(t):
    s = 1.0
    s -= 0.7 * e_io(seg(t, 11.4, 12.0)) * (1 - e_io(seg(t, 13.05, 13.15)))
    s -= 0.75 * e_io(seg(t, 13.3, 13.5)) * (1 - e_io(seg(t, 16.3, 16.5)))
    return max(0.1, s)


_TW = np.arange(0, 20.5, 1 / 240)
_TWS = np.cumsum([_speed(x) for x in _TW]) / 240


def ptime(t):
    return float(np.interp(t, _TW, _TWS))


# ---------------------------------------------------------------- hair / cloth sim
CHAINS = {
    'yasuo': [('hair', hair_anchor, 8, 15.0, 0.9, 0.3), ('sash0', lambda J: sash_anchor(J, 0), 6, 14.0, 1.0, 0.1),
              ('sash1', lambda J: sash_anchor(J, 1), 5, 13.0, 1.0, 0.1)],
    'yone': [('hair', hair_anchor, 10, 15.0, 1.0, 0.25), ('sash0', lambda J: sash_anchor(J, 0), 6, 14.0, 1.0, 0.1),
             ('coat', lambda J: sash_anchor(J, 2), 7, 20.0, 1.2, 0.12)],
}


def _simulate(choreo, name, t0=-1.0, t1=20.05, hz=240):
    specs = CHAINS[name]
    dt = 1 / hz
    state = {}
    J = solve(choreo(0))
    for key, anc, n, seglen, grav, stiff in specs:
        a = anc(J)
        pts = [[a[0] - J['f'] * seglen * i, a[1] + 0.3 * seglen * i] for i in range(n)]
        state[key] = (pts, [p[:] for p in pts])
    frames = {}
    nframes = 601
    t = t0
    fi = 0
    while t < t1 and fi < nframes:
        J = solve(choreo(max(t, 0.0)))
        w = wind(max(t, 0.0))
        for key, anc, n, seglen, grav, stiff in specs:
            p, pp = state[key]
            a = anc(J)
            newp = []
            for i in range(n):
                ph = i * 0.7
                gust = w * (1.0 + 0.35 * math.sin(t * 7.3 + ph) + 0.2 * math.sin(t * 13.1 + ph * 1.7))
                ax = gust * 4.5 * (0.4 + i / n)
                ay = 900 * grav - abs(w) * 1.5 * math.sin(t * 5.1 + ph)
                vx = (p[i][0] - pp[i][0]) * 0.985
                vy = (p[i][1] - pp[i][1]) * 0.985
                newp.append([p[i][0] + vx + ax * dt * dt, p[i][1] + vy + ay * dt * dt])
            newp[0] = [a[0], a[1]]
            if key == 'hair':
                wx, wy = a[0] - J['f'] * seglen * 0.9, a[1] - seglen * 0.05
                newp[1][0] += (wx - newp[1][0]) * stiff
                newp[1][1] += (wy - newp[1][1]) * stiff
            for _ in range(4):
                for i in range(1, n):
                    dx = newp[i][0] - newp[i - 1][0]
                    dy = newp[i][1] - newp[i - 1][1]
                    L = math.hypot(dx, dy) or 1e-6
                    k = seglen / L
                    newp[i][0] = newp[i - 1][0] + dx * k
                    newp[i][1] = newp[i - 1][1] + dy * k
                if key == 'hair':
                    for i in range(2, n):
                        sx = 2 * newp[i - 1][0] - newp[i - 2][0]
                        sy = 2 * newp[i - 1][1] - newp[i - 2][1]
                        newp[i][0] += (sx - newp[i][0]) * 0.03
                        newp[i][1] += (sy - newp[i][1]) * 0.03
            state[key] = (newp, p)
        while fi < nframes and t >= fi / 30 - 1e-9:
            frames[fi] = {k: [tuple(x) for x in state[k][0]] for k in state}
            fi += 1
        t += dt
    return frames


def _cache_key():
    import hashlib, os
    h = hashlib.md5()
    for fn in ('choreo.py', 'rig.py'):
        h.update(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), fn), 'rb').read())
    return h.hexdigest()


def _load_all():
    import pickle, os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sim_cache.pkl')
    key = _cache_key()
    if os.path.exists(path):
        try:
            with open(path, 'rb') as fh:
                k, data = pickle.load(fh)
            if k == key:
                return data
        except Exception:
            pass
    data = {'yasuo': _simulate(YAS, 'yasuo'), 'yone': _simulate(YON, 'yone'),
            'spirit': _simulate(SPI, 'yone', t0=SPIRIT_T0 - 0.3)}
    with open(path, 'wb') as fh:
        pickle.dump((key, data), fh)
    return data


_SIM = {}


def chains_for(who, t):
    if not _SIM:
        _SIM.update(_load_all())
    fr = _SIM[who]
    i = int(round(t * 30))
    i = min(max(i, min(fr)), max(fr))
    return fr[i]

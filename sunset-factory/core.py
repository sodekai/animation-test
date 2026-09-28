"""Shared helpers: math, easing, keyframe tracks, colours, paper textures, compositing."""
import math
import numpy as np
import cairo

W, H = 1080, 1920
FPS = 30
DUR = 20.0
NF = int(round(DUR * FPS))
TAU = 2 * math.pi
D2R = math.pi / 180


# ----------------------------------------------------------------- math / easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, a, b):
    if b == a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def e_io(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def e_o(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def e_i(t):
    t = clamp(t)
    return t ** 3


def e_s(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def e_o2(t):
    t = clamp(t)
    return 1 - (1 - t) ** 2


def e_i2(t):
    t = clamp(t)
    return t * t


def e_back(t, s=1.9):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def e_elastic(t):
    t = clamp(t)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (TAU / 3)) + 1


EASES = {'io': e_io, 'o': e_o, 'i': e_i, 's': e_s, 'lin': clamp, 'back': e_back,
         'o2': e_o2, 'i2': e_i2, 'el': e_elastic}


def lerpv(a, b, t):
    if isinstance(a, (tuple, list)):
        return tuple(lerp(x, y, t) for x, y in zip(a, b))
    return lerp(a, b, t)


class Track:
    """Keyframes (time, value[, ease]). Ease applies to the segment ending at that key.
    Values may be numbers, tuples or callables of t (evaluated lazily)."""

    def __init__(self, *keys):
        self.k = [(k[0], k[1], k[2] if len(k) > 2 else 'io') for k in keys]

    @staticmethod
    def _v(v, t):
        return v(t) if callable(v) else v

    def __call__(self, t):
        k = self.k
        if t <= k[0][0]:
            return self._v(k[0][1], t)
        for i in range(1, len(k)):
            if t < k[i][0]:
                t0, v0, _ = k[i - 1]
                t1, v1, e = k[i]
                if e == 'step':
                    return self._v(v0, t)
                w = EASES[e]((t - t0) / (t1 - t0))
                return lerpv(self._v(v0, t), self._v(v1, t), w)
        return self._v(k[-1][1], t)


class Steps:
    """Discrete value changes: (time, value)."""

    def __init__(self, *keys):
        self.k = keys

    def __call__(self, t):
        v = self.k[0][1]
        for tk, vk in self.k:
            if t >= tk:
                v = vk
        return v


def hexc(h, a=None):
    h = h.lstrip('#')
    c = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return c if a is None else c + (a,)


def mixc(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def shade(c, f):
    if f <= 1:
        return tuple(x * f for x in c[:3])
    return tuple(x + (1 - x) * (f - 1) for x in c[:3])


def hash01(i, salt=0):
    x = math.sin(i * 127.1 + salt * 311.7) * 43758.5453
    return x - math.floor(x)


# ----------------------------------------------------------------- paths
def rrect(c, x, y, w, h, r):
    r = max(0.01, min(r, w / 2, h / 2))
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def star_path(c, x, y, r, rot=0.0, n=5, inner=0.47):
    for k in range(2 * n):
        rr = r if k % 2 == 0 else r * inner
        a = rot - math.pi / 2 + k * math.pi / n
        px, py = x + rr * math.cos(a), y + rr * math.sin(a)
        if k == 0:
            c.move_to(px, py)
        else:
            c.line_to(px, py)
    c.close_path()


def sparkle_path(c, x, y, r, rot=0.0, pinch=0.18):
    """4-point twinkle."""
    pts = []
    for k in range(4):
        a = rot + k * math.pi / 2
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    c.move_to(*pts[0])
    for k in range(4):
        p1 = pts[(k + 1) % 4]
        c.curve_to(x + (pts[k][0] - x) * pinch, y + (pts[k][1] - y) * pinch,
                   x + (p1[0] - x) * pinch, y + (p1[1] - y) * pinch, p1[0], p1[1])
    c.close_path()


def gear_path(c, x, y, r, teeth, rot, depth=0.2, hole=0.32):
    ri = r * (1 - depth)
    n = teeth
    for k in range(n):
        a0 = rot + k * TAU / n
        s = TAU / n
        pts = [(a0, ri), (a0 + s * 0.12, r), (a0 + s * 0.42, r), (a0 + s * 0.54, ri)]
        for j, (a, rr) in enumerate(pts):
            px, py = x + rr * math.cos(a), y + rr * math.sin(a)
            if k == 0 and j == 0:
                c.move_to(px, py)
            else:
                c.line_to(px, py)
    c.close_path()
    if hole > 0:
        c.new_sub_path()
        c.arc_negative(x, y, r * hole, TAU, 0)
        c.close_path()


def wavy_poly(c, fn_y, x0, x1, step=8, first=True):
    xs = np.arange(x0, x1 + (step if x1 > x0 else -step), step if x1 > x0 else -step)
    for i, x in enumerate(xs):
        y = fn_y(x)
        if i == 0 and first:
            c.move_to(x, y)
        else:
            c.line_to(x, y)


# ----------------------------------------------------------------- paper grain
_KEEP = []


def _band_noise(rng, size, f0, f1):
    w = rng.standard_normal((size, size))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    f = np.hypot(fx, fy) + 1e-9
    fc = math.sqrt(f0 * f1)
    bw = 0.5 * math.log(f1 / f0)
    m = np.exp(-((np.log(f) - math.log(fc)) ** 2) / (2 * bw * bw))
    r = np.real(np.fft.ifft2(F * m))
    return r / (r.std() + 1e-9)


def make_grain(size=512, seed=1, amp=0.085, fibers=320):
    rng = np.random.default_rng(seed)
    n = (0.55 * _band_noise(rng, size, 0.22, 0.5) + 0.45 * _band_noise(rng, size, 0.05, 0.14)
         + 0.40 * _band_noise(rng, size, 0.006, 0.03))
    n /= n.std()
    fw = cairo.ImageSurface(cairo.FORMAT_A8, size, size)
    fb = cairo.ImageSurface(cairo.FORMAT_A8, size, size)
    cw, cb = cairo.Context(fw), cairo.Context(fb)
    for i in range(fibers):
        cc = cw if rng.random() < 0.6 else cb
        x, y = rng.uniform(0, size, 2)
        ang = rng.uniform(0, TAU)
        ln = rng.uniform(6, 34)
        bend = rng.uniform(-6, 6)
        cc.set_source_rgba(0, 0, 0, rng.uniform(0.35, 0.9))
        cc.set_line_width(rng.uniform(0.5, 1.3))
        dx, dy = math.cos(ang) * ln, math.sin(ang) * ln
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                cc.move_to(x + ox, y + oy)
                cc.curve_to(x + ox + dx * 0.3 - dy * bend / ln, y + oy + dy * 0.3 + dx * bend / ln,
                            x + ox + dx * 0.7 + dy * bend / ln, y + oy + dy * 0.7 - dx * bend / ln,
                            x + ox + dx, y + oy + dy)
                cc.stroke()
    fw.flush()
    fb.flush()

    def a8(s):
        st = s.get_stride()
        return np.ndarray((size, st), np.uint8, s.get_data())[:, :size].astype(np.float32) / 255

    a = n * amp + a8(fw) * 0.10 - a8(fb) * 0.075
    alpha = np.clip(np.abs(a), 0, 1)
    A = (alpha * 255).astype(np.uint8)
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., 3] = A
    wv = np.where(a > 0, A, 0).astype(np.uint8)
    arr[..., 0] = wv
    arr[..., 1] = wv
    arr[..., 2] = wv
    surf = cairo.ImageSurface.create_for_data(arr, cairo.FORMAT_ARGB32, size, size)
    _KEEP.append(arr)
    pat = cairo.SurfacePattern(surf)
    pat.set_extend(cairo.EXTEND_REPEAT)
    pat.set_filter(cairo.FILTER_BILINEAR)
    return pat


GRAIN = make_grain(512, seed=7)
GRAIN_BIG = make_grain(512, seed=11, amp=0.06, fibers=120)   # used scaled up for mottling

SHC = (0.20, 0.09, 0.08)


def paper(c, fill, seed=0, grain=1.0, rim=0.22, sh=(2.0, 3.0, 0.20), mottle=0.0):
    """Fill current path as a piece of cut paper: tiny drop shadow, colour, grain, light cut rim."""
    path = c.copy_path()
    if sh:
        dx, dy, a = sh
        c.save()
        m = c.get_matrix()
        c.identity_matrix()
        c.translate(dx, dy)
        c.transform(m)
        c.new_path()
        c.append_path(path)
        c.set_source_rgba(*SHC, a)
        c.fill()
        c.restore()
    c.new_path()
    c.append_path(path)
    if isinstance(fill, cairo.Pattern):
        c.set_source(fill)
    elif len(fill) == 4:
        c.set_source_rgba(*fill)
    else:
        c.set_source_rgb(*fill)
    c.fill_preserve()
    c.save()
    c.clip_preserve()
    if mottle > 0:
        GRAIN_BIG.set_matrix(cairo.Matrix(xx=0.25, yy=0.25, x0=(seed * 57.3) % 512, y0=(seed * 31.9) % 512))
        c.set_source(GRAIN_BIG)
        c.paint_with_alpha(mottle)
    if grain > 0:
        GRAIN.set_matrix(cairo.Matrix(x0=(seed * 173.3) % 512, y0=(seed * 97.1) % 512))
        c.set_source(GRAIN)
        c.paint_with_alpha(grain)
    if rim > 0:
        c.set_line_width(3.2)
        c.set_source_rgba(1, 0.98, 0.93, rim)
        c.stroke_preserve()
    c.restore()
    c.new_path()


def pstroke(c, col, width, sh=(2.0, 3.0, 0.2), cap=cairo.LINE_CAP_ROUND):
    path = c.copy_path()
    c.set_line_cap(cap)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    if sh:
        dx, dy, a = sh
        c.save()
        m = c.get_matrix()
        c.identity_matrix()
        c.translate(dx, dy)
        c.transform(m)
        c.new_path()
        c.append_path(path)
        c.set_source_rgba(*SHC, a)
        c.set_line_width(width)
        c.stroke()
        c.restore()
    c.new_path()
    c.append_path(path)
    c.set_line_width(width)
    if len(col) == 4:
        c.set_source_rgba(*col)
    else:
        c.set_source_rgb(*col)
    c.stroke()


def glow(c, x, y, r, col, a, op=cairo.OPERATOR_SCREEN):
    if a <= 0.001 or r <= 1:
        return
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *col, a)
    g.add_color_stop_rgba(0.35, *col, a * 0.45)
    g.add_color_stop_rgba(0.7, *col, a * 0.12)
    g.add_color_stop_rgba(1, *col, 0)
    c.save()
    c.set_operator(op)
    c.set_source(g)
    c.arc(x, y, r, 0, TAU)
    c.fill()
    c.restore()


# ----------------------------------------------------------------- layers
SW, SH = W // 8, H // 8


def new_layer(cam):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_matrix(cam)
    return s, c


def composite(dst, surf, sh=None):
    """Composite a layer onto dst with a soft paper drop shadow computed from its alpha."""
    if sh:
        dx, dy, sig, a = sh
        surf.flush()
        buf = np.ndarray((H, W, 4), np.uint8, surf.get_data())
        al = buf[:, :, 3].reshape(SH, 8, SW, 8).mean(axis=(1, 3)).astype(np.float32)
        if al.max() > 0:
            from scipy.ndimage import gaussian_filter
            al = gaussian_filter(al, sig, mode='nearest')
            v = np.clip(al, 0, 255).astype(np.uint8)
            m = np.empty((SH, SW, 4), np.uint8)
            m[..., 0] = v
            m[..., 1] = v
            m[..., 2] = v
            m[..., 3] = v
            ms = cairo.ImageSurface.create_for_data(m, cairo.FORMAT_ARGB32, SW, SH)
            dst.save()
            dst.identity_matrix()
            dst.translate(dx, dy)
            dst.scale(W / SW, H / SH)
            mp = cairo.SurfacePattern(ms)
            mp.set_filter(cairo.FILTER_BILINEAR)
            mp.set_extend(cairo.EXTEND_PAD)
            dst.set_source_rgba(*SHC, a)
            dst.mask(mp)
            dst.restore()
    dst.save()
    dst.identity_matrix()
    dst.set_source_surface(surf, 0, 0)
    dst.paint()
    dst.restore()


NIGHT_TINT = hexc('#1F235E')


def tint(c, a, col=NIGHT_TINT):
    if a <= 0.001:
        return
    c.save()
    c.identity_matrix()
    c.set_operator(cairo.OPERATOR_ATOP)
    c.set_source_rgba(*col, a)
    c.paint()
    c.restore()

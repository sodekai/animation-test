"""Procedural soundtrack for the duel, synced to the choreography data."""
import math
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
from core import DUR, seg, clamp, lerp, e_io
from rig import solve, blade_points
import choreo as C

SR = 48000
N = int(DUR * SR) + SR // 2
rng = np.random.default_rng(12)
DRY = np.zeros((2, N))
SEND = np.zeros((2, N))


def tt(d):
    return np.arange(int(d * SR)) / SR


def mixs(*arrs):
    n = max(len(a) for a in arrs)
    out = np.zeros(n)
    for a in arrs:
        out[:len(a)] += a
    return out


def place(sig, t0, gain=1.0, pan=0.0, rev=0.2):
    i0 = int(t0 * SR)
    if i0 >= N or len(sig) == 0:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    a = (clamp(pan, -1, 1) + 1) * math.pi / 4
    gl, gr = math.cos(a), math.sin(a)
    s = sig[:n] * gain
    DRY[0, i0:i0 + n] += s * gl
    DRY[1, i0:i0 + n] += s * gr
    SEND[0, i0:i0 + n] += s * gl * rev
    SEND[1, i0:i0 + n] += s * gr * rev


def filt(x, kind, f, order=2):
    sos = signal.butter(order, f, btype=kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)


def fade(x, fi=0.003, fo=0.02):
    a, b = int(fi * SR), int(fo * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b and len(x) > b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def panx(x):
    return clamp((x - 540) / 520, -1, 1) * 0.8


# ------------------------------------------------------------------ instruments
def partials(freq, d, parts, a=0.001):
    t = tt(d)
    s = np.zeros(len(t))
    for r, amp, dec in parts:
        s += amp * np.sin(2 * np.pi * freq * r * t + r * 1.7) * np.exp(-t / dec)
    return fade(s * np.minimum(1, t / a), 0, 0.05)


def clang(freq=820, d=1.6, power=1.0):
    ring = partials(freq, d, ((1, 1, 0.5), (2.41, 0.8, 0.35), (3.83, 0.6, 0.25), (5.11, 0.45, 0.18), (7.3, 0.3, 0.1),
                              (1.52, 0.5, 0.4)))
    n = int(0.08 * SR)
    crack = filt(rng.standard_normal(n), 'high', 1800) * env(n, 0.0005, 0.018)
    thump = partials(90, 0.3, ((1, 1, 0.08),)) * power
    return mixs(ring * 0.5, crack * 1.2, thump * 0.9)


def taiko(f0=62, d=1.4, hit=1.0):
    t = tt(d)
    f = f0 * (1 + 0.5 * np.exp(-t / 0.03))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.35 * d))
    n = int(0.05 * SR)
    skin = filt(rng.standard_normal(n), 'band', [150, 1200]) * env(n, 0.0005, 0.012) * 0.8 * hit
    return fade(mixs(body, skin))


def whoosh(d, f0, f1, shape=1.5):
    n = int(d * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        k = i / n
        fc = f0 * (f1 / f0) ** k
        lo, hi = max(40, fc * 0.6), min(SR / 2 - 100, fc * 1.5)
        seg_ = x[max(0, i - 2048):i + blk]
        y = filt(seg_, 'band', [lo, hi])
        out[i:i + blk] = y[-len(out[i:i + blk]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** shape


def draw_shing(d=0.9):
    n = int(d * SR)
    t = np.arange(n) / SR
    scrape = filt(rng.standard_normal(n), 'band', [3500, 9000]) * np.exp(-t / 0.18) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * t))
    ring = partials(2350, d, ((1, 1, 0.45), (1.61, 0.6, 0.3), (2.33, 0.4, 0.2)))
    return mixs(scrape * 0.7, ring * 0.35)


def click(freq=3000, d=0.03):
    n = int(d * SR)
    return filt(rng.standard_normal(n) * env(n, 0.0003, d * 0.2), 'band', [freq * 0.6, min(freq * 1.6, 20000)])


def flute(notes, bpm_t=None):
    """notes: list of (start, dur, freq, amp). Breathy shakuhachi-ish voice with a slide into each note."""
    total = max(s + d for s, d, f, a in notes) + 0.6
    out = np.zeros(int(total * SR))
    for s, d, f, a in notes:
        n = int((d + 0.5) * SR)
        t = np.arange(n) / SR
        slide = f * (2 ** (-1.2 / 12 * np.exp(-t / 0.07)))
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
        ph = 2 * np.pi * np.cumsum(slide * vib) / SR
        tone = np.sin(ph) + 0.22 * np.sin(2 * ph + 0.5) + 0.06 * np.sin(3 * ph)
        breath = filt(rng.standard_normal(n), 'band', [f * 0.8, min(f * 3.2, 12000)]) * 0.35
        e = np.clip(t / 0.09, 0, 1) * np.clip((d + 0.35 - t) / 0.35, 0, 1)
        sig = (tone + breath * (0.6 + 0.4 * np.exp(-t / 0.15))) * e * a
        i = int(s * SR)
        m = min(n, len(out) - i)
        out[i:i + m] += sig[:m]
    return out


def pad(chord, d, amp):
    t = tt(d)
    s = np.zeros(len(t))
    for f in chord:
        for det in (-0.004, 0.0, 0.005):
            ph = 2 * np.pi * f * (1 + det) * t
            s += sum(np.sin(k * ph) / k ** 1.3 for k in range(1, 6))
    s = filt(s, 'low', 1400)
    e = np.clip(t / (d * 0.35), 0, 1) * np.clip((d - t) / (d * 0.35), 0, 1)
    return s * e * amp / len(chord)


def shimmer(d, amp=1.0):
    t = tt(d)
    s = np.zeros(len(t))
    for i in range(24):
        f = 1800 * 2 ** (rng.uniform(0, 2.2))
        st = rng.uniform(0, d * 0.7)
        e = np.exp(-np.maximum(0, t - st) / 0.35) * (t >= st)
        s += np.sin(2 * np.pi * f * t) * e * rng.uniform(0.3, 1)
    return s * amp / 8


# ------------------------------------------------------------------ analysis of the choreography
def tip_speeds(ch, drawn_fn, idx, t0, t1, hz=200):
    ts = np.arange(t0, t1, 1 / hz)
    tips = []
    for t in ts:
        J = solve(ch(t))
        hand, ang = (J['haN'], J['sN']) if idx == 0 else (J['haF'], J['sF'])
        tips.append(blade_points(hand, ang)[1] if drawn_fn(t)[min(idx, len(drawn_fn(t)) - 1)] else (np.nan, np.nan))
    tips = np.array(tips, float)
    v = np.hypot(*np.gradient(tips, axis=0).T) * hz
    return ts, np.nan_to_num(v), tips


NWH = []


def main(out):
    ts = np.linspace(0, DUR, int(DUR * 200) + 1)
    tsN = np.arange(N) / SR

    # --- wind bed following the scene's wind, very quiet during the frozen aftermath
    wv = np.array([C.wind(t) for t in ts])
    quiet = np.array([1 - 0.75 * seg(t, 13.35, 13.6) * (1 - seg(t, 16.3, 16.6)) for t in ts])
    wamp = np.interp(tsN, ts, np.clip(0.012 + wv / 5000, 0, 0.1) * quiet)
    wcut = np.interp(tsN, ts, 500 + wv * 3)
    noise = rng.standard_normal(N)
    lo = filt(noise, 'band', [180, 900])
    hi = filt(noise, 'band', [900, 3500])
    mixk = np.clip((wcut - 500) / 1500, 0, 1)
    wind = (lo * (1 - mixk * 0.5) + filt(hi, 'low', 2500) * mixk * 0.4) * wamp * (0.8 + 0.2 * np.sin(2 * np.pi * 0.23 * tsN))
    DRY[0] += wind * 0.9
    DRY[1] += wind * (0.9 + 0.1 * np.sin(2 * np.pi * 0.17 * tsN))

    # --- music: low drone building to the final pass, flute phrases, taiko
    D = 73.42
    place(pad([D, D * 1.5, D * 2], 13.4, 0.22) * np.clip((13.4 - tt(13.4)) / 0.08, 0, 1), -0.2, 1.0, 0, 0.3)
    notes = [(0.25, 0.7, 587.3, 0.10), (1.05, 0.45, 698.5, 0.09), (1.55, 1.1, 659.3, 0.10), (2.75, 0.4, 587.3, 0.08),
             (3.1, 0.45, 523.3, 0.06)]
    place(flute(notes), 0, 1.0, -0.1, 0.55)
    notes2 = [(0.0, 0.8, 440.0, 0.09), (0.9, 0.5, 523.3, 0.08), (1.5, 1.4, 587.3, 0.09), (3.0, 0.5, 523.3, 0.07),
              (3.55, 1.0, 440.0, 0.08)]
    place(flute(notes2), 16.9, 1.0, 0.1, 0.6)
    place(pad([D * 2, D * 2 * 1.2, D * 3, D * 4], 3.4, 0.16), 16.6, 1.0, 0, 0.5)

    for tb, g in ((0.9, 0.5), (2.65, 0.45), (3.5, 0.55), (5.0, 0.9), (6.95, 0.7), (7.45, 0.55), (8.2, 0.4), (9.27, 0.55),
                  (10.02, 0.6), (10.55, 0.6), (XS := C.XSLASH_T + 0.3, 1.0), (19.2, 0.35)):
        place(taiko(58 if g > 0.6 else 66, 1.6), tb, g, 0, 0.35)
    # tension roll before the pass (accelerating)
    t = 11.6
    gap = 0.55
    k = 0
    while t < C.PASS_T0 - 0.02:
        prog = (t - 11.6) / (C.PASS_T0 - 11.6)
        place(taiko(74 + 10 * (k % 2), 0.6, 0.6), t, 0.12 + 0.3 * prog, (-0.3 if k % 2 else 0.3), 0.3)
        t += gap
        gap = max(0.07, gap * 0.82)
        k += 1
    ten = tt(1.6)
    tone = np.sin(2 * np.pi * (1500 + 400 * ten / 1.6) * ten) * (ten / 1.6) ** 2 * 0.04
    place(tone, C.PASS_T0 - 1.6, 1.0, 0, 0.3)

    # --- Yone appears / dissolves
    place(shimmer(1.8, 0.8) + 0 * tt(1.8), 0.35, 0.5, 0.4, 0.8)
    sw = tt(1.6)
    swell = filt(rng.standard_normal(len(sw)), 'low', 300) * np.sin(np.pi * sw / 1.6) ** 2 * 0.5
    place(swell, 0.3, 0.6, 0.4, 0.4)
    place(whoosh(0.5, 300, 90), 2.55, 0.3, 0.4, 0.3)          # mask flare growl
    place(shimmer(1.6, 0.8), C.YONE_OUT[0], 0.45, -0.4, 0.8)
    place(whoosh(1.4, 400, 3000, 2.0), C.YONE_OUT[0], 0.15, -0.4, 0.6)

    # --- draws
    place(draw_shing(), 3.47, 0.55, -0.4, 0.35)
    place(whoosh(0.5, 400, 2500), 3.4, 0.22, -0.4, 0.2)       # wind burst
    place(draw_shing(), 3.52, 0.45, 0.45, 0.35)
    place(draw_shing(), 3.58, 0.35, 0.5, 0.35)

    # --- blade whooshes, auto-detected from tip speed peaks
    for ch, dfn, idxs, key in ((C.YAS, C.drawn_yasuo, (0,), 'yasuo'), (C.YON, C.drawn_yone, (0, 1), 'yone'),
                               (C.SPI, lambda t: [C.SPIRIT_T0 <= t < C.SPIRIT_T1] * 2, (0, 1), 'spirit')):
        for idx in idxs:
            tsv, v, tips = tip_speeds(ch, dfn, idx, 0, DUR)
            vs = np.convolve(v, np.ones(5) / 5, 'same')
            peaks, _ = signal.find_peaks(vs, height=900, distance=int(0.14 * 200))
            for p in peaks:
                tp = tsv[p]
                sp = vs[p]
                d = 0.28
                g = clamp((sp - 700) / 3500, 0.1, 0.42)
                f0 = 500 + min(sp, 4000) * 0.3
                x = tips[p][0] if not np.isnan(tips[p][0]) else 540
                place(whoosh(d, f0, f0 * 2.4, 1.2), tp - d * 0.55, g * (0.8 if key == 'spirit' else 1), panx(x), 0.2)
                NWH.append(tp)

    # --- clashes
    for i, (tc, x, y, pw) in enumerate(C.CLASHES):
        place(clang(700 + 140 * i, 1.8, pw), tc, 0.55 * (0.6 + 0.4 * pw), panx(x), 0.45)
    gt = tt(0.45)
    grind = filt(rng.standard_normal(len(gt)), 'band', [2000, 7000]) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * gt)) * np.sin(np.pi * gt / 0.45)
    place(grind, 5.08, 0.18, 0, 0.3)

    # --- movement: dashes, landings, skid
    for tb, x in ((4.55, 330), (4.55, 760), (7.08, 470), (8.2, 285), (C.PASS_T0, 330), (C.PASS_T0, 750)):
        n = int(0.14 * SR)
        thud = filt(rng.standard_normal(n), 'low', 700) * env(n, 0.001, 0.04)
        place(mixs(thud, taiko(110, 0.2) * 0.3), tb, 0.35, panx(x), 0.15)
    sk = tt(0.45)
    skid = filt(rng.standard_normal(len(sk)), 'band', [700, 4000]) * np.sin(np.pi * sk / 0.45) * (0.7 + 0.3 * rng.random(len(sk)))
    place(skid, 7.72, 0.18, 0.5, 0.15)
    place(whoosh(0.5, 300, 1400), 4.55, 0.35, 0, 0.2)         # the charge
    place(whoosh(0.45, 250, 1200), 6.3, 0.2, -0.1, 0.2)        # jump
    place(whoosh(0.4, 900, 300), 7.72, 0.2, -0.3, 0.2)        # leap back

    # --- Steel Tempest: charge swirl, tornado roar, X cut
    ct = tt(0.8)
    charge = whoosh(0.8, 500, 2600, 1.0) * (ct / 0.8)
    place(charge, 8.5, 0.35, -0.4, 0.3)
    tor_d = C.TORNADO_CUT - C.TORNADO_T0 + 0.35
    tn = tt(tor_d)
    roar = mixs(whoosh(tor_d, 250, 700, 0.7), 0.6 * whoosh(tor_d, 1500, 3000, 0.7))
    roar *= (0.7 + 0.3 * np.sin(2 * np.pi * 9 * tn))
    for ch in range(2):
        pn = np.interp(tn, [0, tor_d], [-0.4, 0.5])
        a = (pn + 1) * np.pi / 4
        gch = np.cos(a) if ch == 0 else np.sin(a)
        i0 = int(C.TORNADO_T0 * SR)
        DRY[ch, i0:i0 + len(tn)] += roar[:len(tn)] * gch * 0.45
        SEND[ch, i0:i0 + len(tn)] += roar[:len(tn)] * gch * 0.1
    place(draw_shing(0.7), C.TORNADO_CUT - 0.02, 0.5, 0.35, 0.4)
    place(whoosh(0.7, 3000, 300), C.TORNADO_CUT, 0.4, 0.35, 0.4)

    # --- spirit form
    st = tt(0.9)
    ghost = sum(np.sin(2 * np.pi * f * st) for f in (293.7, 296.5, 440.0, 443.0)) * np.sin(np.pi * st / 0.9) ** 2 * 0.08
    place(ghost, C.SPIRIT_T0 - 0.05, 1.0, 0.4, 0.8)
    place(whoosh(0.35, 400, 3000), 10.25, 0.35, 0.3, 0.3)
    rt = tt(0.35)
    rev = whoosh(0.35, 3000, 400) * (rt / 0.35) ** 2
    place(rev, 10.72, 0.4, 0.3, 0.4)
    place(partials(1320, 1.2, ((1, 1, 0.5), (2.76, 0.3, 0.3))), 11.03, 0.12, 0.5, 0.7)

    # --- standoff details
    place(partials(3100, 1.2, ((1, 1, 0.4), (1.5, 0.4, 0.3))), 12.35, 0.12, -0.4, 0.7)   # blade glint
    place(whoosh(0.6, 200, 80), 12.5, 0.3, 0.4, 0.3)                                    # mask flare

    # --- the pass: whoosh, slash, then silence with a lingering ring
    place(whoosh(0.3, 600, 5000), C.PASS_T0 - 0.03, 0.8, 0, 0.3)
    place(draw_shing(1.2), C.PASS_X, 0.8, 0, 0.5)
    place(clang(1900, 2.5, 0.3), C.PASS_X, 0.25, 0, 0.6)
    ring = partials(2600, 3.0, ((1, 1, 1.2),)) * 0.3
    place(ring, C.PASS_X + 0.05, 0.12, 0, 0.3)

    # --- sheathing clicks + the delayed X-slash
    for dtk, x in ((0.0, 740), (0.025, 340)):
        place(mixs(click(3200, 0.03), partials(2400, 0.3, ((1, 1, 0.06), (1.7, 0.5, 0.04)))), C.SHEATH_T + dtk, 0.45, panx(x), 0.3)
    place(whoosh(0.25, 1200, 7000), C.XSLASH_T - 0.05, 0.6, 0, 0.3)
    place(draw_shing(1.4), C.XSLASH_T, 0.7, 0, 0.5)
    place(shimmer(1.5, 1.2), C.XSLASH_T + 0.3, 0.5, 0, 0.8)
    place(whoosh(1.2, 2500, 200), C.XSLASH_T + 0.3, 0.4, 0, 0.5)

    # --- reverb, master
    irn = int(2.2 * SR)
    ir_t = np.arange(irn) / SR
    ir = np.stack([filt(rng.standard_normal(irn), 'low', 6000) * np.exp(-ir_t / 0.55) for _ in range(2)])
    ir[:, :int(0.02 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True)) * 3.0
    wet = np.stack([signal.fftconvolve(SEND[c], ir[c])[:N] for c in range(2)])
    mix = DRY + wet
    mix = filt(mix, 'high', 28)
    mix = mix[:, :int(DUR * SR)]
    fo = int(0.6 * SR)
    mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    mix = mix / np.abs(mix).max() * 0.95
    mix = np.tanh(mix * 1.6) / np.tanh(1.6)
    mix = mix / np.abs(mix).max() * 0.89
    rms = 20 * np.log10(np.sqrt((mix ** 2).mean()) + 1e-9)
    print(f'RMS {rms:.1f} dBFS, whooshes at', ' '.join(f'{x:.2f}' for x in sorted(NWH)))
    wavfile.write(out, SR, (mix.T * 32767).astype(np.int16))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav')

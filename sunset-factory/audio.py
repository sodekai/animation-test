"""Procedural sound design, synced to the animation's own motion data."""
import math
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
from core import DUR, seg, clamp, e_io
import world as Wd
from workers import ACTOR_A, ACTOR_B

SR = 48000
N = int(DUR * SR) + SR // 2
rng = np.random.default_rng(5)
DRY = np.zeros((2, N))
SEND = np.zeros((2, N))


def tt(d):
    return np.arange(int(d * SR)) / SR


def pan_gains(p):
    a = (p + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def place(sig, t0, gain=1.0, pan=0.0, rev=0.15):
    i0 = int(t0 * SR)
    if i0 >= N or len(sig) == 0:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    gl, gr = pan_gains(pan)
    s = sig[:n] * gain
    DRY[0, i0:i0 + n] += s * gl
    DRY[1, i0:i0 + n] += s * gr
    SEND[0, i0:i0 + n] += s * gl * rev
    SEND[1, i0:i0 + n] += s * gr * rev


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    sos = signal.butter(order, f, btype='low', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    sos = signal.butter(order, f, btype='high', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def env_ad(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
    return e


def fade(x, fi=0.003, fo=0.01):
    n = len(x)
    a, b = int(fi * SR), int(fo * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


# ------------------------------------------------------------------ instruments
def mixs(*arrs):
    n = max(len(a) for a in arrs)
    out = np.zeros(n)
    for a in arrs:
        out[:len(a)] += a
    return out


def click(freq=2500, d=0.025, q=0.5):
    n = int(d * SR)
    x = rng.standard_normal(n) * env_ad(n, 0.0005, d * 0.25)
    return bp(x, freq * (1 - q), freq * (1 + q))


def knock(freq=180, d=0.18, noise=0.4):
    t = tt(d)
    f = freq * (1 + 0.6 * np.exp(-t / 0.012))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_ad(len(t), 0.001, d * 0.25)
    nz = lp(rng.standard_normal(len(t)), 2000) * env_ad(len(t), 0.0005, 0.012) * noise
    return fade(mixs(s, nz))


def bell(freq, d=1.2, partials=((1, 1, 1), (2.76, 0.45, 0.55), (5.4, 0.25, 0.3), (8.93, 0.12, 0.2)), a=0.002):
    t = tt(d)
    s = np.zeros(len(t))
    for r, amp, dec in partials:
        s += amp * np.sin(2 * np.pi * freq * r * t + r) * np.exp(-t / (d * dec * 0.35))
    s *= np.minimum(1, t / a)
    return fade(s, 0.0, 0.05)


def glass(freq=2600, d=0.5):
    return bell(freq, d, ((1, 1, 1), (1.53, 0.5, 0.7), (2.61, 0.35, 0.5), (3.9, 0.2, 0.3)), a=0.0008)


def metal(freq=520, d=0.6):
    return mixs(bell(freq, d, ((1, 1, 1), (2.63, 0.7, 0.6), (4.14, 0.5, 0.4), (6.2, 0.3, 0.25)), a=0.0008),
                click(3000, 0.02) * 0.8)


def whoosh(d, f0, f1, amp_curve=None):
    n = int(d * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        k = i / n
        fc = f0 * (f1 / f0) ** k
        seg_ = x[max(0, i - 2048):i + blk]
        y = bp(seg_, fc * 0.7, fc * 1.4)
        out[i:i + blk] = y[-len(out[i:i + blk]):]
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5 if amp_curve is None else amp_curve
    return out * e


def pop():
    t = tt(0.09)
    f = 620 * np.exp(-t / 0.03) + 180
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.0008, 0.03)
    return fade(mixs(s, click(1800, 0.015) * 0.9))


def boing(f0=330):
    t = tt(0.5)
    f = f0 * (1 - 0.35 * t) * (1 + 0.04 * np.sin(2 * np.pi * 14 * t))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.004, 0.14)
    return fade(s)


def rustle(d=0.28):
    n = int(d * SR)
    x = bp(rng.standard_normal(n), 1500, 6000) * (0.6 + 0.4 * rng.random(n) ** 3)
    return x * np.sin(np.pi * np.linspace(0, 1, n)) ** 2


def chirp_cricket():
    out = np.zeros(int(0.16 * SR))
    for k in range(3):
        t = tt(0.028)
        s = np.sin(2 * np.pi * 4700 * t) * np.sin(np.pi * np.linspace(0, 1, len(t)))
        i = int(k * 0.045 * SR)
        out[i:i + len(s)] += s
    return out


def slurp():
    t = tt(0.22)
    f = 180 + 520 * (t / 0.22) ** 1.5
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.22) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * t))
    return fade(s)


# ------------------------------------------------------------------ continuous beds
def bed_from_curve(times, amps, freqs, kind='hum'):
    """Synthesize a continuous tone whose amp/pitch follow curves sampled at `times`."""
    ts = np.arange(N) / SR
    a = np.interp(ts, times, amps)
    f = np.interp(ts, times, freqs)
    ph = 2 * np.pi * np.cumsum(f) / SR
    if kind == 'hum':
        s = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph + 0.3)
    else:  # motor: buzzy saw, lowpassed
        s = sum(np.sin(k * ph) / k for k in range(1, 9))
        s = lp(s, 900)
    return s * a


def main(out):
    ts = np.linspace(0, DUR, int(DUR * 200) + 1)

    # factory hum + room tone (quieter as night settles)
    night = np.array([Wd.night_amount(t) for t in ts])
    hum_amp = 0.05 * (1 - 0.45 * night) * np.clip(ts / 0.4, 0, 1) * np.clip((DUR - ts) / 0.6, 0, 1)
    hum = bed_from_curve(ts, hum_amp, 55 + 0 * ts)
    place(lp(hum, 400), 0, 1.0, 0, 0.05)
    room = lp(rng.standard_normal(N), 700) * 0.012
    place(room, 0, 1.0, 0, 0.0)

    # gear ticks (tick-tock) and chimney chugs
    t = 0.12
    i = 0
    while t < DUR - 0.2:
        g = 0.05 * (1 - 0.4 * Wd.night_amount(t))
        place(click(1500 if i % 2 else 1100, 0.02, 0.3), t, g, -0.15, 0.1)
        t += 0.33
        i += 1
    for k in range(40):
        t0 = -3 + (k) * 0.62
        if 0 < t0 < DUR:
            place(lp(knock(70, 0.25, 0.6), 400), t0, 0.12 * (1 - 0.5 * Wd.night_amount(t0)), -0.35, 0.1)

    # shutter roll-up: motor + slat rattles + stop clunk
    motor = bed_from_curve(np.array([0, 0.3, 0.4, 1.05, 1.15, 1.3]), np.array([0, 0, 0.09, 0.09, 0, 0]),
                           np.array([80, 80, 95, 125, 125, 125]), 'motor')
    place(motor, 0, 1.0, -0.3, 0.1)
    for k in range(16):
        tk = 0.38 + k * 0.045
        place(click(2200 + 300 * (k % 3), 0.03, 0.4), tk, 0.18, -0.35, 0.15)
    place(knock(120, 0.25), 1.15, 0.5, -0.35, 0.2)
    # warm glow swell as the sun is revealed
    sw = tt(2.0)
    swell = sum(np.sin(2 * np.pi * f * sw) * a for f, a in ((261.6, 1), (392.0, 0.6), (523.3, 0.4), (659.3, 0.25)))
    swell *= np.sin(np.pi * np.clip(sw / 2.0, 0, 1)) ** 2 * 0.045
    place(swell, 0.55, 1.0, -0.2, 0.5)

    # conveyor: rumble + roller clacks + crank squeaks
    bo = np.array([Wd.belt_offset(t) for t in ts])
    bspeed = np.gradient(bo, ts)
    rum = lp(rng.standard_normal(N), 250) * np.interp(np.arange(N) / SR, ts, np.clip(bspeed / 220, 0, 1)) * 0.2
    place(rum, 0, 1.0, 0.0, 0.05)
    last = 0
    for t, o in zip(ts, bo):
        if int(o // 28) != last:
            last = int(o // 28)
            x = Wd.sun_belt_x(t)
            place(knock(420 + 60 * (last % 3), 0.06, 0.8), t, 0.16, (x - 540) / 600, 0.1)
    lastr = 0
    for t, o in zip(ts, bo):
        rev = int((o / 13.0) // (2 * math.pi))
        if rev != lastr:
            lastr = rev
            tq = tt(0.12)
            sq = np.sin(2 * np.pi * np.cumsum(1300 - 400 * tq / 0.12) / SR) * np.sin(np.pi * tq / 0.12) * 0.5
            place(sq, t, 0.05, -0.7, 0.15)
    # sun hits the bumper
    place(knock(95, 0.35, 0.5), 4.45, 0.75, 0.4, 0.2)
    place(boing(300), 4.46, 0.18, 0.45, 0.25)

    # footsteps + hop landings
    for actor, pan0 in ((ACTOR_A, 0.0), (ACTOR_B, 0.0)):
        last = None
        for t in np.arange(0, DUR, 1 / 240):
            x = actor.xt(t)
            v = abs(actor.xt(t + 0.01) - actor.xt(t - 0.01)) / 0.02
            k = int(math.floor(x * 2 * math.pi / 80 / math.pi))
            if last is not None and k != last and v > 40:
                place(lp(knock(240 if actor.name == 'A' else 300, 0.07, 1.2), 1800), t, 0.07,
                      (x - 540) / 700, 0.08)
            last = k
    for tl in (0.98, 11.44):
        place(knock(200, 0.12, 1.0), tl, 0.18, -0.1, 0.1)
        place(knock(230, 0.12, 1.0), tl + 0.015, 0.18, 0.1, 0.1)
    place(knock(260, 0.12, 1.0), 15.1, 0.14, 0.2, 0.1)

    # poles: slurp out of the bucket, flip whoosh, telescoping clacks, roller squish, retract, lean
    for who, tp, tf, te, pan in (('B', 5.55, 5.75, 6.05, -0.3), ('A', 5.6, 5.8, 6.08, 0.25)):
        place(slurp(), tp, 0.07, pan, 0.15)
        place(whoosh(0.3, 500, 1800), tf, 0.10, pan, 0.2)
        for k in range(3):
            tk = te + k / 3 * (Wd.PT0 - te) + 0.03
            place(mixs(click(2600 + 400 * k, 0.03, 0.3), 0.4 * metal(1600 + 200 * k, 0.12)), tk, 0.13, pan, 0.2)
        for k in range(3):
            tk = Wd.PT1 + 0.04 + k / 3 * (8.45 - Wd.PT1 - 0.02)
            place(mixs(click(2900 - 300 * k, 0.03, 0.3), 0.4 * metal(1900 - 200 * k, 0.12)), tk, 0.12, pan, 0.2)
        place(knock(330, 0.08, 1.0), 8.74, 0.1, pan, 0.1)
    for rx_fn, pan_sign in ((Wd.pink_rx, 1), (Wd.orange_rx, -1)):
        rx = np.array([rx_fn(t) for t in ts])
        sp = np.abs(np.gradient(rx, ts))
        amp = np.clip(sp / 700, 0, 1) * 0.13
        tsN = np.arange(N) / SR
        a = np.interp(tsN, ts, amp)
        am = 0.65 + 0.35 * np.sin(2 * np.pi * 7 * tsN)
        sq = bp(rng.standard_normal(N), 500, 1600) * a * am
        pan_c = np.interp(tsN, ts, np.clip((rx - 540) / 600, -1, 1))
        l, r = np.cos((pan_c + 1) * np.pi / 4), np.sin((pan_c + 1) * np.pi / 4)
        DRY[0] += sq * l
        DRY[1] += sq * r
        SEND[0] += sq * l * 0.15
        SEND[1] += sq * r * 0.15

    # crane: motor following tip/cable speed, winch ratchet, claw clanks
    tipx = np.array([Wd.TIPX(t) for t in ts])
    tipy = np.array([Wd.TIPY(t) for t in ts])
    cab = np.array([Wd.CABLE(t) for t in ts])
    v = np.hypot(np.gradient(tipx, ts), np.gradient(tipy, ts)) + np.abs(np.gradient(cab, ts))
    mamp = np.clip(v / 350, 0, 1) * 0.085
    mfreq = 62 + np.clip(v, 0, 900) * 0.07
    place(bed_from_curve(ts, mamp, mfreq, 'motor'), 0, 1.0, 0.25, 0.1)
    acc = 0.0
    for i in range(1, len(ts)):
        acc += abs(cab[i] - cab[i - 1])
        if acc > 14:
            acc = 0
            place(click(3200, 0.018, 0.3), ts[i], 0.06, 0.3, 0.1)
    place(hp(whoosh(0.35, 3000, 5000), 2000), 8.45, 0.05, 0.3, 0.1)       # hydraulic hiss
    place(metal(520, 0.7), 9.2, 0.22, 0.35, 0.25)
    place(knock(150, 0.2, 0.5), 9.2, 0.25, 0.35, 0.2)
    place(metal(610, 0.5), 11.06, 0.14, 0.0, 0.25)
    place(click(2400, 0.02), 10.94, 0.2, 0.0, 0.2)

    # sun placed: chime + shimmer
    for f, g, d in ((1046.5, 0.22, 2.2), (1568.0, 0.12, 1.8), (2093.0, 0.07, 1.4)):
        place(bell(f, d), 11.0, g, 0.0, 0.5)
    place(whoosh(0.8, 2500, 8000) * 0.8, 10.95, 0.05, 0.0, 0.4)

    # little heart pops while they admire the sun
    for th, f0 in ((11.62, 700), (11.8, 820), (12.35, 760), (12.75, 880)):
        bt = tt(0.09)
        bf = f0 * (1 + 0.5 * bt / 0.09)
        place(fade(np.sin(2 * np.pi * np.cumsum(bf) / SR) * np.sin(np.pi * bt / 0.09) ** 2), th, 0.05, 0.0, 0.3)

    # crate bump, jar wobble tinks, fall, clonk, roll, cork pop
    place(knock(170, 0.22, 0.9), Wd.BUMP_T, 0.45, 0.45, 0.2)
    for tk, f in ((14.12, 2700), (14.3, 3100), (14.46, 2500)):
        place(glass(f, 0.45), tk, 0.13, 0.45, 0.3)
        for j in range(4):
            place(glass(4200 + 700 * j, 0.15), tk + 0.01 + 0.02 * j, 0.03, 0.45, 0.3)
    place(whoosh(0.25, 800, 300), 14.62, 0.08, 0.35, 0.1)
    place(knock(130, 0.25, 0.8), Wd.JAR_LAND_T, 0.5, 0.3, 0.2)
    place(glass(1900, 0.6), Wd.JAR_LAND_T, 0.16, 0.3, 0.3)
    rl = tt(0.4)
    roll = lp(rng.standard_normal(len(rl)), 900) * np.exp(-rl / 0.15) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * rl))
    place(roll, Wd.JAR_LAND_T + 0.03, 0.12, 0.2, 0.1)
    place(pop(), 15.05, 0.5, 0.05, 0.3)
    place(knock(420, 0.06, 1.0), 15.67, 0.08, -0.25, 0.1)        # cork lands

    # magical sparkle: rising shimmer + a cascade of chimes per star (launch) and twinkles (arrival)
    shim = mixs(whoosh(1.6, 1500, 9000), 0.6 * whoosh(1.6, 3000, 12000))
    place(lp(shim, 8000), 15.03, 0.09, 0.0, 0.6)
    scale = [1046.5, 1174.7, 1318.5, 1568.0, 1760.0]
    for i, s in enumerate(Wd.STARS):
        f = scale[i % 5] * (2 if (i * 7) % 3 == 0 else 1) * (0.5 if i % 11 == 0 else 1)
        pan = clamp((s['E'][0] - 540) / 540, -1, 1) * 0.8
        place(bell(f, 0.9, ((1, 1, 1), (2.0, 0.3, 0.6), (3.0, 0.12, 0.4))), s['s0'], 0.045, pan * 0.4, 0.7)
        place(bell(f * 2, 0.6, ((1, 1, 1), (2.76, 0.2, 0.5))), s['s0'] + s['d'], 0.022, pan, 0.8)
    # soft night pad
    pt = tt(5.0)
    pad = sum(np.sin(2 * np.pi * f * pt + ph) * a for f, a, ph in
              ((220.0, 1, 0), (277.2, 0.7, 1), (329.6, 0.6, 2), (440.0, 0.3, 3)))
    pad *= np.clip(pt / 1.5, 0, 1) * np.clip((5.0 - pt) / 1.5, 0, 1) * 0.03
    place(lp(pad, 1200), 15.4, 1.0, 0.0, 0.6)

    # night: lamp + window clicks, crickets
    for tk in (16.45, 16.6, 16.75):
        place(click(1800, 0.02), tk, 0.08, 0.1, 0.2)
    place(mixs(click(1200, 0.03), 0.5 * click(2600, 0.02)), 16.6, 0.16, -0.05, 0.2)
    for k in range(18):
        tc = 16.9 + k * 0.33 + 0.08 * math.sin(k * 3.1)
        if tc < DUR - 0.2:
            place(chirp_cricket(), tc, 0.02 + 0.01 * (k % 2), -0.7 if k % 2 else 0.6, 0.35)

    # the shrug: little cloth rustles, then a last twinkle
    place(lp(rustle(), 4000), 18.25, 0.045, -0.2, 0.15)
    place(lp(rustle(), 4000), 18.32, 0.045, 0.2, 0.15)
    place(bell(2093.0, 1.0), 19.25, 0.035, -0.4, 0.8)

    # reverb
    irn = int(1.6 * SR)
    ir_t = np.arange(irn) / SR
    ir = np.stack([lp(rng.standard_normal(irn), 5000) * np.exp(-ir_t / 0.32) for _ in range(2)])
    ir[:, :int(0.012 * SR)] = 0
    ir /= np.abs(ir).sum(axis=1, keepdims=True) ** 0.5 * 12
    wet = np.stack([signal.fftconvolve(SEND[c], ir[c])[:N] for c in range(2)])
    mix = DRY + wet * 1.0
    mix = hp(mix, 30)
    mix = mix[:, :int(DUR * SR)]
    # gentle fade-out at the very end
    fo = int(0.35 * SR)
    mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    # soft limiter + normalize
    peak = np.abs(mix).max()
    mix = mix / peak * 0.9
    mix = np.tanh(mix * 1.4) / np.tanh(1.4)
    mix = mix / np.abs(mix).max() * 0.89
    rms = 20 * np.log10(np.sqrt((mix ** 2).mean()) + 1e-9)
    print(f'peak normalized, RMS {rms:.1f} dBFS')
    wavfile.write(out, SR, (mix.T * 32767).astype(np.int16))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav')

"""Sound design, all synthesised here (no downloaded or licensed audio):
one SFX per event type, peaks frame-aligned at 60 fps, 4-10 dB under the narration;
an ambient pad 7 dB under the narration, ending with the title and +5 dB over it."""
import json, numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import butter, sosfilt, resample_poly

SR, FPS, END = 48000, 60, 60.0
N = int(END * SR)
rng = np.random.default_rng(1125)
WJ = json.load(open('build/words.json'))
def at(line, word, n=0):
    return [w for w in WJ['words'] if w['line'] == line and w['w'].lower() == word.lower()][n]['s']
T = dict(stopped=at(0,'stopped'), planet=at(1,'The'), right=at(2,'Right'), sixteen=at(2,'sixteen'),
         stand=at(3,'Stand'), you=at(3,'you'), play=at(4,'play'), earth5=at(5,'Earth'), now=at(6,'Now'),
         brakes=at(6,'brakes'), air=at(7,'air'), tornado=at(8,'tornado'), oceans=at(9,'oceans'), waves=at(9,'waves'),
         poles=at(9,'poles'), oneday=at(10,'day'), year10=at(10,'year'), six=at(11,'Six'), night=at(11,'night'),
         sunglasses=at(12,'sunglasses'), mask=at(12,'mask'), relax=at(13,'Relax'), slowing=at(13,'slowing'),
         ms=at(13,'milliseconds'), by=at(14,'By'))
T['title'] = WJ['duration'] + 0.36

t_ = lambda d: np.arange(int(d * SR)) / SR
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def env(d, a, r): t = t_(d); return np.minimum(t / max(a, 1e-4), 1) * np.exp(-np.maximum(t - a, 0) / r)

# ---- one sound per event type ----
def s_impact():      # shockwave boom
    t = t_(1.6); f = 38 + 70 * np.exp(-t * 9)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(1.6, .004, .45) + lp(rng.standard_normal(len(t)), 900) * env(1.6, .002, .12) * .6
def s_collapse():    # spin seizing up: downward groan
    t = t_(0.7); f = 160 * np.exp(-t * 3.2) + 35
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) + .3 * np.sin(2 * np.pi * np.cumsum(2.01 * f) / SR)) * env(.7, .02, .25)
def s_whoosh(d=1.6, up=False):
    t = t_(d); n = rng.standard_normal(len(t)); sh = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    if up: sh = (t / d) ** 2.2 * np.exp(-np.maximum(t - .92 * d, 0) * 30)
    lo = bp(n, 250, 1800) * sh; hi = bp(n, 1800, 6000) * sh * .35
    return lo + hi
def s_tick():
    t = t_(0.03); return np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 260) + .4 * hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 400)
def s_tap():         # sign / gag landing
    t = t_(0.25); return (np.sin(2 * np.pi * 820 * t) + .6 * np.sin(2 * np.pi * 1310 * t) + .3 * np.sin(2 * np.pi * 410 * t)) * np.exp(-t * 28)
def s_photon():      # wind front hits the globe
    t = t_(0.9); n = rng.standard_normal(len(t)); return bp(n, 600, 5000) * env(.9, .01, .2) + .5 * np.sin(2 * np.pi * (900 - 500 * t) * t) * env(.9, .005, .15)
def s_play():        # press play: soft pop + chirp
    t = t_(0.35); f = 500 + 900 * (1 - np.exp(-t * 30))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(.35, .003, .08)
def s_light():       # city lights flicker on
    t = t_(1.2); out = np.zeros(len(t))
    for k, f in enumerate([1320, 1760, 2093, 2637]):
        o = int(k * .07 * SR); tt = t[:len(t) - o]; out[o:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 4) * .5
    return out
def s_reveal():      # soft chime for key reveals
    t = t_(1.8); return sum(np.sin(2 * np.pi * f * t) * np.exp(-t * (2.2 + i)) / (i + 1) for i, f in enumerate([587.3, 880, 1174.7, 1760]))
def s_creep():       # oceans draining to the poles (the "ice creep" slot)
    t = t_(1.9); n = rng.standard_normal(len(t)); g = (rng.random(len(t)) < .004) * rng.random(len(t))
    return bp(n, 200, 1200) * np.sin(np.pi * t / 1.9) ** 1.5 * .7 + bp(g, 1500, 6000) * 6 * np.sin(np.pi * t / 1.9)
def s_rewind():      # tape-style reverse sweep, 0.8 s
    t = t_(0.85); f = 2400 * np.exp(-t * 2.2) + 200
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * .4 + bp(rng.standard_normal(len(t)), 800, 5000) * .6) * np.sin(np.pi * t / .85)

# (type, generator, dB below narration, [event times]); peak lands on the event frame
fr = lambda x: round(x * FPS) / FPS
TYPES = [
 ('impact', s_impact, 5, [T['stopped'], T['brakes']]),
 ('collapse', s_collapse, 8, [T['stopped'] + .22, T['brakes'] + .22]),
 ('pullout', lambda: s_whoosh(1.6), 8, [T['planet'] + .5, T['earth5'] + 1.0, T['oneday'] + .6, T['title'] + .8]),
 ('tick', s_tick, 10, [T['sixteen'] + i / 18 for i in range(13)] + [T['air'] + i / 18 for i in range(11)]
                     + [T['oneday'] + .25 + i / 9 for i in range(int((T['year10'] - T['oneday']) * 9))] + [T['ms'] - .2 + i / 14 for i in range(9)]),
 ('pushin', lambda: s_whoosh(1.2, True), 8, [T['stand'] + 1.0, T['now'] + 1.1, T['oceans'] + 1.4, T['by'] + .8]),
 ('tap', s_tap, 7, [T['you'] + .13, T['by'] + .13, T['six'] - .3, T['sunglasses'] - .08, T['mask'] - .08]),
 ('photon', s_photon, 7, [T['air'] + .2]),
 ('play', s_play, 6, [T['play'] + .1]),
 ('light', s_light, 8, [T['night'] + .05]),
 ('reveal', s_reveal, 9, [T['sixteen'] + .05, T['tornado'] + .2, T['year10'] + .1, T['title'] + .1]),
 ('creep', s_creep, 8, [T['poles'] + .9]),
 ('rewind', s_rewind, 6, [T['right'] + .4, T['relax'] + .4]),
]

vo24, sr0 = sf.read('build/vo_24k.wav'); vo = resample_poly(vo24, 2, 1)
vo = np.pad(vo, (0, N - len(vo)))[:N]
speech = vo[np.abs(vo) > 1e-3]; vo_rms = np.sqrt(np.mean(speech ** 2))
sfx = np.zeros((N, 2))
for name, gen, db, times in TYPES:
    s = gen(); s = s / (np.max(np.abs(s)) + 1e-9)
    w = int(.05 * SR); e = np.convolve(s ** 2, np.ones(w) / w, 'same'); pk = int(np.argmax(e))
    act = s[np.abs(s) > .05]; s *= vo_rms * 10 ** (-db / 20) / (np.sqrt(np.mean(act ** 2)) + 1e-9)
    for i, tt in enumerate(times):
        st = int(round(fr(tt) * SR)) - pk
        pan = np.clip(.5 + .15 * np.sin(i * 1.7 + len(name)), 0, 1)
        a, b = max(st, 0), min(st + len(s), N)
        if b <= a: continue
        seg = s[a - st:b - st]; sfx[a:b, 0] += seg * np.sqrt(1 - pan); sfx[a:b, 1] += seg * np.sqrt(pan)

# ---- ambient pad: slow chords, detuned sines, gentle shimmer; ends exactly at the end of the title ----
CH = [[146.83, 220.0, 277.18, 329.63, 440.0], [123.47, 185.0, 246.94, 293.66, 369.99],
      [98.0, 196.0, 246.94, 293.66, 369.99], [110.0, 164.81, 246.94, 277.18, 329.63]]
tt = np.arange(N) / SR; pad = np.zeros((N, 2)); seg = 7.5
for k in range(int(END // seg) + 1):
    t0 = k * seg; ch = CH[k % 4]; a = int(max(t0 - 1.5, 0) * SR); b = min(int((t0 + seg + 2.5) * SR), N)
    if a >= N: break
    x = tt[a:b] - t0; fade = np.clip((x + 1.5) / 3, 0, 1) * np.clip((seg + 2.5 - x) / 3, 0, 1)
    for j, f in enumerate(ch):
        for side, det in ((0, -.6), (1, .6)):
            ph = rng.random() * 6.28
            pad[a:b, side] += (np.sin(2 * np.pi * (f + det) * tt[a:b] + ph) + .25 * np.sin(2 * np.pi * 2 * (f + det) * tt[a:b] + ph)) * fade / (j + 2)
shim = bp(rng.standard_normal(N), 3000, 7000) * (.5 + .5 * np.sin(2 * np.pi * .07 * tt)) * .05
pad[:, 0] += shim; pad[:, 1] += np.roll(shim, 900)
pad = np.stack([lp(pad[:, 0], 2400), lp(pad[:, 1], 2400)], 1)
pad *= (0.5 - 0.5 * np.cos(np.pi * np.clip(tt / 2.0, 0, 1)))[:, None]            # fade in
pad *= np.clip((END - tt) / 1.4, 0, 1)[:, None] ** 1.5                           # ends with the title
pad_rms = np.sqrt(np.mean(pad[int(3 * SR):int(T['title'] * SR)] ** 2))
gain = vo_rms * 10 ** (-7 / 20) / pad_rms
up = 10 ** (5 / 20); ramp = np.clip((tt - T['title'] + .3) / .6, 0, 1)
pad *= (gain * (1 + (up - 1) * ramp))[:, None]

mix = np.stack([vo, vo], 1) + sfx + pad
sf.write('build/mix_raw.wav', mix.astype(np.float32), SR, subtype='FLOAT')
meter = pyln.Meter(SR)
print('raw LUFS %.2f' % meter.integrated_loudness(mix), 'peak dB %.2f' % (20 * np.log10(np.abs(mix).max())))
for nm, x in (('vo', np.stack([vo, vo], 1)), ('sfx', sfx), ('pad', pad)):
    print(nm, 'LUFS %.1f' % meter.integrated_loudness(x))

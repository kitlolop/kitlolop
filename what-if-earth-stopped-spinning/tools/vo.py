"""Narration: Kokoro-82M (ONNX, local) + exact word timings from the model's own
phoneme-duration tensor (/encoder/Clip_output_0, 600 samples per unit @ 24 kHz)."""
import json, sys, re, numpy as np, onnxruntime as ort, soundfile as sf
from kokoro_onnx import Kokoro
M = sys.argv[1]            # models dir
SPEED = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2
SR, HOP = 24000, 600
# (gap_before_seconds, text)   0.24 between sentences, 0.36 before key reveals
LINES = json.load(open('tools/script.json'))
k = Kokoro(f'{M}/kokoro-v1.0.onnx', f'{M}/voices-v1.0.bin')
sess = ort.InferenceSession(f'{M}/kokoro-dur.onnx')
VOICE = k.get_voice_style('bm_george')

out, words, t = [], [], 0.0
for li, (gap, text) in enumerate(LINES):
    ph = k.tokenizer.phonemize(text, 'en-gb')
    toks = k.tokenizer.tokenize(ph)
    known = k.tokenizer.known(ph)
    st = VOICE[len(toks)].reshape(1, 256).astype(np.float32)
    audio, dur = sess.run(None, {'tokens': np.array([[0, *toks, 0]], np.int64), 'style': st,
                                 'speed': np.array([SPEED], np.float32)})
    dur = dur.ravel().astype(int); assert dur.sum() * HOP == len(audio), (dur.sum()*HOP, len(audio))
    edges = np.concatenate([[0], np.cumsum(dur)]) * HOP      # sample edges per token (incl. pads)
    # trim leading/trailing pad silence by energy, keep 40 ms margin
    env = np.abs(audio); thr = env.max() * 0.02
    nz = np.where(env > thr)[0]; a0 = max(0, nz[0] - int(.04*SR)); a1 = min(len(audio), nz[-1] + int(.06*SR))
    if li: t += gap
    # phoneme words: split known-phoneme string on spaces; token i+1 <-> known[i]
    tw = [m for m in re.finditer(r'[^ ]+', known)]
    txt_words = text.replace('—', ' ').split()
    pw = []
    for m in tw:
        seg = known[m.start():m.end()]
        core = re.sub(r'[^\wɐ-ʯˈˌːæðŋɔəɛɪʊʌʃʒθ]', '', seg)
        if not core: continue          # pure punctuation token
        i0 = m.start() + (len(seg) - len(seg.lstrip(',.!?;:"')))
        i1 = m.end() - (len(seg) - len(seg.rstrip(',.!?;:"')))
        pw.append(((edges[i0 + 1] - a0) / SR, (edges[i1 + 1] - a0) / SR))
    if len(pw) != len(txt_words):
        print('WORD MISMATCH', li, len(pw), len(txt_words), known, file=sys.stderr)
    for w, (s, e) in zip(txt_words, pw):
        words.append({'w': re.sub(r'[^\w\'-]', '', w), 'line': li, 's': round(t + s, 3), 'e': round(t + e, 3)})
    seg = audio[a0:a1]
    out.append(np.zeros(int(round(gap * SR)) if li else 0, np.float32)); out.append(seg)
    t += len(seg) / SR
vo = np.concatenate(out)
sf.write('build/vo_24k.wav', vo, SR)
json.dump({'duration': round(len(vo)/SR, 3), 'words': words}, open('build/words.json', 'w'), indent=0)
nw = len(words); speech = sum(len(o) for o in out[1::2]) / SR
print(f'VO {len(vo)/SR:.2f}s  words {nw}  speech-only wpm {nw/speech*60:.0f}')
for li in range(len(LINES)):
    ws = [w for w in words if w['line'] == li]
    print(f"{ws[0]['s']:6.2f}-{ws[-1]['e']:6.2f}  " + ' '.join(f"{w['w']}@{w['s']:.2f}" for w in ws))

"""Thai narration: Microsoft neural voice th-TH-NiwatNeural (via edge-tts) at its natural rate,
with per-word timings from the service's WordBoundary events. Cue words are mapped to the
same event keys the animation uses (build/words.json)."""
import asyncio, io, json, os, subprocess, sys, numpy as np, soundfile as sf
VOICE, SR = 'th-TH-NiwatNeural', 24000
RATE = sys.argv[1] if len(sys.argv) > 1 else '+0%'
import edge_tts
LINES = json.load(open('tools/script_th.json'))
async def synth(text):
    c = edge_tts.Communicate(text, VOICE, rate=RATE, proxy=os.environ.get('HTTPS_PROXY'), boundary='WordBoundary')
    mp3, wb = b'', []
    async for ch in c.stream():
        if ch['type'] == 'audio': mp3 += ch['data']
        elif ch['type'] == 'WordBoundary': wb.append((ch['offset'] / 1e7, ch['duration'] / 1e7, ch['text']))
    return mp3, wb
def decode(mp3):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', '-', '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], input=mp3, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)
PREROLL = 0.45   # let the opening shot breathe before the first word
out, words, t = [np.zeros(int(PREROLL * SR), np.float32)], [], PREROLL
for li, L in enumerate(LINES):
    mp3, wb = asyncio.run(synth(L['text'])); a = decode(mp3)
    env = np.abs(a); nz = np.where(env > env.max() * 0.015)[0]
    a0 = max(0, nz[0] - int(.03 * SR)); a1 = min(len(a), nz[-1] + int(.08 * SR))
    if li: t += L['gap']
    joined, starts = '', []
    for (o, d, w) in wb: starts.append((len(joined), o)); joined += w
    for key, sub in L['cues']:
        if sub == '': s = wb[0][0]
        else:
            i = joined.find(sub); assert i >= 0, (li, sub, joined)
            s = [o for (pos, o) in starts if pos <= i][-1]
        words.append({'w': key, 'line': li, 's': round(t + s - a0 / SR, 3)})
    seg = a[a0:a1]
    if li: out.append(np.zeros(int(round(L['gap'] * SR)), np.float32))
    out.append(seg); t += len(seg) / SR
    print(f"{li:2d} {words[-len(L['cues'])]['s']:6.2f}  {len(seg)/SR:5.2f}s  " + ' '.join(f"{w['w']}@{w['s']:.2f}" for w in words if w['line'] == li))
vo = np.concatenate(out)
sf.write('build/vo_24k.wav', vo, SR)
json.dump({'duration': round(len(vo) / SR, 3), 'lang': 'th', 'voice': VOICE, 'rate': RATE, 'words': words}, open('build/words.json', 'w'), ensure_ascii=False, indent=0)
print(f'VO {len(vo)/SR:.2f}s')

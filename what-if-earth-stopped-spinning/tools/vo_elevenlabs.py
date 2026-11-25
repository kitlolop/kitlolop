"""Thai narration with ElevenLabs (text-to-speech *with timestamps*).

Key: either a Network secret for api.elevenlabs.io (header xi-api-key, injected by the
session proxy) or the env var ELEVENLABS_API_KEY.

  python3 tools/vo_elevenlabs.py voices                 # list voices in the account
  python3 tools/vo_elevenlabs.py models                 # list models that support Thai
  python3 tools/vo_elevenlabs.py make <voice_id> [model_id] [--fit SECONDS]

`make` writes build/vo_24k.wav and build/words.json (same cue keys the animation uses),
generating line by line with previous/next text for natural continuity.
Voice settings: stability .5, similarity .75 (per the brief).

API responses are cached in build/el_cache/ (keyed by request), so re-running `make`
(e.g. with another --fit) does not spend characters again.
--fit S: if the assembled VO is longer than S seconds, every spoken line is sped up by the
same factor with ffmpeg atempo (pitch preserved; gaps untouched) and the cue times scaled.
The animation ends at 60 s and needs ~4.5 s after the VO for the title, so use --fit 55.
Also writes build/subs_th.srt: each line split at its spaces into cues of <= 34 characters,
timed from the same character alignment."""
import base64, hashlib, json, os, subprocess, sys, urllib.request, numpy as np, soundfile as sf

API = 'https://api.elevenlabs.io'
SR = 24000
KEY = os.environ.get('ELEVENLABS_API_KEY', 'injected-by-proxy')

def call(path, body=None):
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)

def thai_models():
    ms = call('/v1/models')
    return [m for m in ms if m.get('can_do_text_to_speech') and any(l.get('language_id') == 'th' for l in m.get('languages', []))]

cmd = sys.argv[1] if len(sys.argv) > 1 else 'voices'
if cmd == 'voices':
    for v in call('/v2/voices?page_size=100').get('voices', []):
        lab = v.get('labels') or {}
        print(f"{v['voice_id']}  {v['name'][:40]:40s}  {v.get('category','')}  {lab.get('gender','')} {lab.get('accent','')} {lab.get('age','')}")
    sys.exit()
if cmd == 'models':
    for m in thai_models(): print(m['model_id'], '-', m.get('name'))
    sys.exit()

args = sys.argv[2:]
FIT = None
if '--fit' in args:
    i = args.index('--fit'); FIT = float(args[i + 1]); del args[i:i + 2]
voice = args[0]
model = args[1] if len(args) > 1 else thai_models()[0]['model_id']
LINES = json.load(open('tools/script_th.json'))
PREROLL = 0.45
os.makedirs('build/el_cache', exist_ok=True)

def tts(body):
    path = f'/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128'
    key = hashlib.sha256(json.dumps([path, body], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    f = f'build/el_cache/{key}.json'
    if os.path.exists(f): return json.load(open(f))
    r = call(path, body); json.dump(r, open(f, 'w')); return r

def decode(mp3, tempo=1.0):
    af = [] if tempo == 1.0 else ['-af', f'atempo={tempo:.5f}']
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', '-', *af, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                                        input=mp3, capture_output=True, check=True).stdout, np.float32)

RAW = []
for li, L in enumerate(LINES):
    body = {'text': L['text'], 'model_id': model,
            'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75},
            'previous_text': LINES[li - 1]['text'] if li else None,
            'next_text': LINES[li + 1]['text'] if li + 1 < len(LINES) else None}
    if model == 'eleven_v3':   # v3 does not take request stitching fields
        body.pop('previous_text'); body.pop('next_text')
    RAW.append(tts({k: v for k, v in body.items() if v is not None}))

def assemble(tempo):
  out, words, subs, t = [np.zeros(int(PREROLL * SR), np.float32)], [], [], PREROLL
  for li, (L, r) in enumerate(zip(LINES, RAW)):
    a = decode(base64.b64decode(r['audio_base64']), tempo)
    al = r.get('alignment') or r.get('normalized_alignment')
    chars, st = ''.join(al['characters']), [x / tempo for x in al['character_start_times_seconds']]
    env = np.abs(a); nz = np.where(env > env.max() * 0.015)[0]
    a0 = max(0, nz[0] - int(.03 * SR)); a1 = min(len(a), nz[-1] + int(.08 * SR))
    if li: t += L['gap']
    for key, sub in L['cues']:
        i = 0 if sub == '' else chars.find(sub)
        assert i >= 0, (li, sub)
        j = next(k for k in range(i, len(chars)) if not chars[k].isspace())
        words.append({'w': key, 'line': li, 's': round(t + st[j] - a0 / SR, 3)})
    seg = a[a0:a1]
    off = t - a0 / SR
    cues, pos = [], 0
    for ph in L['text'].split(' '):
        i = chars.find(ph, pos); assert i >= 0, (li, ph); pos = i + len(ph)
        if cues and len(cues[-1][1]) + 1 + len(ph) <= 34: cues[-1][1] += ' ' + ph
        else: cues.append([off + st[i], ph])
    end = t + len(seg) / SR
    for k, (cs, txt) in enumerate(cues):
        subs.append((max(cs, t), cues[k + 1][0] if k + 1 < len(cues) else end, txt))
    if li: out.append(np.zeros(int(round(L['gap'] * SR)), np.float32))
    out.append(seg); t += len(seg) / SR
  return np.concatenate(out), words, subs

tempo = 1.0
vo, words, subs = assemble(tempo)
if FIT and len(vo) / SR > FIT:
    gaps = PREROLL + sum(L['gap'] for L in LINES[1:])
    for _ in range(4):   # atempo + trimming is not exactly linear: refine
        tempo *= (len(vo) / SR - gaps) / (FIT - 0.05 - gaps)
        vo, words, subs = assemble(tempo)
        if len(vo) / SR <= FIT: break
for li in range(len(LINES)):
    print(f"{li:2d}  " + ' '.join(f"{w['w']}@{w['s']:.2f}" for w in words if w['line'] == li))
sf.write('build/vo_24k.wav', vo, SR)
json.dump({'duration': round(len(vo) / SR, 3), 'lang': 'th', 'engine': 'elevenlabs', 'voice': voice, 'model': model,
           'tempo': round(tempo, 4), 'words': words}, open('build/words.json', 'w'), ensure_ascii=False, indent=0)
ts = lambda x: f'{int(x//3600):02d}:{int(x%3600//60):02d}:{int(x%60):02d},{int(round(x%1*1000)) % 1000:03d}'
open('build/subs_th.srt', 'w').write(''.join(f'{n}\n{ts(a)} --> {ts(b)}\n{txt}\n\n' for n, (a, b, txt) in enumerate(subs, 1)))
print(f'VO {len(vo)/SR:.2f}s  model {model}  tempo x{tempo:.3f}')

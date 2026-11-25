"""Thai narration with ElevenLabs (text-to-speech *with timestamps*).

Key: either a Network secret for api.elevenlabs.io (header xi-api-key, injected by the
session proxy) or the env var ELEVENLABS_API_KEY.

  python3 tools/vo_elevenlabs.py voices                 # list voices in the account
  python3 tools/vo_elevenlabs.py models                 # list models that support Thai
  python3 tools/vo_elevenlabs.py make <voice_id> [model_id]

`make` writes build/vo_24k.wav and build/words.json (same cue keys the animation uses),
generating line by line with previous/next text for natural continuity.
Voice settings: stability .5, similarity .75 (per the brief)."""
import base64, json, os, subprocess, sys, urllib.request, numpy as np, soundfile as sf

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

voice = sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else thai_models()[0]['model_id']
LINES = json.load(open('tools/script_th.json'))
PREROLL = 0.45
out, words, t = [np.zeros(int(PREROLL * SR), np.float32)], [], PREROLL
for li, L in enumerate(LINES):
    body = {'text': L['text'], 'model_id': model,
            'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75},
            'previous_text': LINES[li - 1]['text'] if li else None,
            'next_text': LINES[li + 1]['text'] if li + 1 < len(LINES) else None}
    if model == 'eleven_v3':   # v3 does not take request stitching fields
        body.pop('previous_text'); body.pop('next_text')
    r = call(f'/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128', {k: v for k, v in body.items() if v is not None})
    mp3 = base64.b64decode(r['audio_base64'])
    a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', '-', '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                                     input=mp3, capture_output=True, check=True).stdout, np.float32)
    al = r.get('alignment') or r.get('normalized_alignment')
    chars, st = ''.join(al['characters']), al['character_start_times_seconds']
    env = np.abs(a); nz = np.where(env > env.max() * 0.015)[0]
    a0 = max(0, nz[0] - int(.03 * SR)); a1 = min(len(a), nz[-1] + int(.08 * SR))
    if li: t += L['gap']
    for key, sub in L['cues']:
        i = 0 if sub == '' else chars.find(sub)
        assert i >= 0, (li, sub)
        j = next(k for k in range(i, len(chars)) if not chars[k].isspace())
        words.append({'w': key, 'line': li, 's': round(t + st[j] - a0 / SR, 3)})
    seg = a[a0:a1]
    if li: out.append(np.zeros(int(round(L['gap'] * SR)), np.float32))
    out.append(seg); t += len(seg) / SR
    print(f"{li:2d} {len(seg)/SR:5.2f}s  " + ' '.join(f"{w['w']}@{w['s']:.2f}" for w in words if w['line'] == li))
vo = np.concatenate(out)
sf.write('build/vo_24k.wav', vo, SR)
json.dump({'duration': round(len(vo) / SR, 3), 'lang': 'th', 'engine': 'elevenlabs', 'voice': voice, 'model': model, 'words': words},
          open('build/words.json', 'w'), ensure_ascii=False, indent=0)
print(f'VO {len(vo)/SR:.2f}s  model {model}')

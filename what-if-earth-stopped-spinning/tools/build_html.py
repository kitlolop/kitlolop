import base64, json, pathlib
src = pathlib.Path('src/index.src.html').read_text()
words = json.load(open('build/words.json'))
geo = pathlib.Path('build/geo.json').read_text()
font = base64.b64encode(pathlib.Path('build/fredoka-latin.woff2').read_bytes()).decode()
out = src.replace('/*@WORDS@*/null', json.dumps(words, separators=(',', ':'))).replace('/*@GEO@*/null', geo).replace('/*@FONT@*/', font)
pathlib.Path('index.html').write_text(out); print('index.html', len(out))

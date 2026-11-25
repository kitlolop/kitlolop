import base64, json, pathlib
src = pathlib.Path('src/index.src.html').read_text()
words = json.load(open('build/words.json'))
geo = pathlib.Path('build/geo.json').read_text()
font = base64.b64encode(pathlib.Path('build/fredoka-latin.woff2').read_bytes()).decode()
out = src.replace('/*@WORDS@*/null', json.dumps(words, separators=(',', ':'))).replace('/*@GEO@*/null', geo).replace('/*@FONT@*/', font)\
    .replace('/*@FONT_TH5@*/', base64.b64encode(pathlib.Path('build/mitr-thai-500.woff2').read_bytes()).decode())\
    .replace('/*@FONT_TH6@*/', base64.b64encode(pathlib.Path('build/mitr-thai-600.woff2').read_bytes()).decode())
pathlib.Path('index.html').write_text(out); print('index.html', len(out))

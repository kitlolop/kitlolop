import json, sys
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1]; meta = json.load(open(f'{d}/beats.json')); cols = 5; tw, th = 576, 324
rows = (len(meta) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 34)), (8, 16, 30))
try: fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
except Exception: fnt = ImageFont.load_default()
dr = ImageDraw.Draw(sheet)
for m in meta:
    im = Image.open(m['f']).convert('RGB').resize((tw, th), Image.LANCZOS)
    x, y = (m['i'] % cols) * tw, (m['i'] // cols) * (th + 34)
    sheet.paste(im, (x, y + 34)); dr.text((x + 8, y + 7), f"{m['i']+1:02d}  {m['t']:.2f}s  {m['name']}", fill=(143, 216, 230), font=fnt)
sheet.save(sys.argv[2]); print(sheet.size)

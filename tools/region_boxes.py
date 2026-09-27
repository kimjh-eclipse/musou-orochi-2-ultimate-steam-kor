"""Label boxes inside a sub-rectangle of a texture (alpha outside is ignored), with a numbered preview.
usage: region_boxes.py <entry> <tex> x0 y0 x1 y1 [gap]"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
e, ti = int(sys.argv[1]), int(sys.argv[2])
x0, y0, x1, y1 = map(int, sys.argv[3:7])
gap = float(sys.argv[7]) if len(sys.argv) > 7 else 0.8
d, t, im = load(e, ti)
a = np.asarray(im.getchannel("A")).copy()
mask = np.zeros_like(a)
mask[y0:y1 + 1, x0:x1 + 1] = a[y0:y1 + 1, x0:x1 + 1]
bx = boxes(mask, gap)
prev = Image.new("RGBA", (x1 - x0 + 1, y1 - y0 + 1), (40, 44, 60, 255))
prev.alpha_composite(im.crop((x0, y0, x1 + 1, y1 + 1)))
dr = ImageDraw.Draw(prev)
for k, (a0, b0, a1, b1) in enumerate(bx):
    dr.rectangle((a0 - x0, b0 - y0, a1 - x0, b1 - y0), outline=(0, 255, 0, 255))
    dr.text((a0 - x0 + 2, b0 - y0), str(k), fill=(255, 255, 0, 255))
s = min(1.0, 1400 / max(prev.size))
prev.resize((int(prev.width * s), int(prev.height * s))).save(ROOT / f"extract/probe/region_{e}_t{ti}.png")
print(json.dumps(bx))

"""box_index_view.py <entry> <tex> <gap> : numbered label boxes over the CHS art, split into tiles
extract/peek/bix_<entry>_<tex>_<n>.png (each <=1400 wide)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
e, ti, gap = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
d, t, im = load(e, ti)
bx = boxes(np.asarray(im.getchannel("A")), gap=gap)
bb = im.getchannel("A").getbbox()
bg = Image.new("RGBA", im.size, (30, 34, 48, 255))
bg.alpha_composite(im)
dr = ImageDraw.Draw(bg)
for i, b in enumerate(bx):
    dr.rectangle(b, outline=(255, 60, 60, 255))
    dr.rectangle((b[0], b[1], b[0] + 26, b[1] + 16), fill=(0, 0, 0, 255)); dr.text((b[0] + 2, b[1] + 2), str(i), fill=(255, 255, 0, 255))
tw, th = 1400, 600
n = 0
for y in range(bb[1], bb[3], th):
    for x in range(bb[0], bb[2], tw):
        bg.crop((x, y, x + tw, y + th)).save(ROOT / f"extract/peek/bix_{e}_{ti}_{n}.png")
        n += 1
print(len(bx), "boxes", n, "tiles")

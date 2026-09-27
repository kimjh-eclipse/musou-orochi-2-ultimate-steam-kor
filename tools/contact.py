"""contact.py out.png e:t e:t ... : CHS textures cropped to alpha bbox, stacked with labels (max width 1400)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
arcs = {}
tiles = []
for it in sys.argv[2:]:
    parts = it.split(":")
    lang = parts[0] if len(parts) == 3 else "CHS"
    e, t = map(int, parts[-2:])
    d = arcs.setdefault(lang, Archive(lang)).read(e)
    im = decode(d, parse(d)["tex"][t])
    bb = im.getchannel("A").getbbox()
    if not bb:
        continue
    im = im.crop(bb)
    s = min(1.0, 1380 / im.width, 500 / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
    tiles.append((it, im))
W = 1400
H = sum(im.height + 22 for _, im in tiles)
out = Image.new("RGBA", (W, H), (40, 44, 60, 255))
dr = ImageDraw.Draw(out)
y = 0
for name, im in tiles:
    dr.text((4, y + 4), name, fill=(255, 255, 0, 255))
    out.alpha_composite(im, (10, y + 20))
    y += im.height + 22
out.save(ROOT / "extract/peek" / sys.argv[1])
print(H)

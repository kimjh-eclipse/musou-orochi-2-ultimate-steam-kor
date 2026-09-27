"""Before/after sheet for chosen textures of one image spec: preview_sheet.py <entry> <tex> [<tex> ...]"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
from pc_idx import Archive
from g1t_pc import parse, decode
from image_labels import apply_labels

ROOT = Path(__file__).resolve().parents[1]
e = int(sys.argv[1])
want = [int(x) for x in sys.argv[2:]]
spec = json.loads((ROOT / f"mapping/images/{e:05d}.json").read_text(encoding="utf-8"))
ts = {x["tex"]: x for x in spec["textures"]}
d = Archive("CHS").read(e)
g = parse(d)
rows = []
for ti in want:
    t = g["tex"][ti]
    im = decode(d, t)
    new, _ = apply_labels(im, ts[ti]["labels"])
    pair = Image.new("RGBA", (t["w"] * 2 + 12, t["h"]), (46, 50, 66, 255))
    pair.alpha_composite(im, (0, 0))
    pair.alpha_composite(new, (t["w"] + 12, 0))
    rows.append((ti, pair))
W = max(p.width for _, p in rows)
sheet = Image.new("RGBA", (W, sum(p.height + 4 for _, p in rows)), (30, 30, 36, 255))
y = 0
for ti, p in rows:
    sheet.alpha_composite(p, (0, y))
    ImageDraw.Draw(sheet).text((2, y + 2), str(ti), fill=(255, 255, 0, 255))
    y += p.height + 4
s = min(1.0, 1500 / sheet.width)
sheet.resize((int(sheet.width * s), int(sheet.height * s))).save(ROOT / f"extract/preview/sheet_{e}.png")

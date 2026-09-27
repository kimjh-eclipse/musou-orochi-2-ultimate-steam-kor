"""Save a texture (optionally cropped to its alpha bbox) over a checker/dark background for viewing.
usage: crop_tex.py <part> <entry> <tex> [scale]"""
import sys
from pathlib import Path
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
part, e, ti = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
scale = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
d = Archive(part).read(e)
t = parse(d)["tex"][ti]
im = decode(d, t)
bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
if bb:
    im = im.crop(bb)
bg = Image.new("RGBA", im.size, (40, 44, 60, 255))
bg.alpha_composite(im)
if scale != 1.0:
    bg = bg.resize((int(bg.width * scale), int(bg.height * scale)), Image.LANCZOS)
out = ROOT / f"extract/probe/{part}_{e}_t{ti}.png"
bg.save(out)
print(out, "bbox", bb, "size", im.size)

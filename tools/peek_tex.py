"""Dump CHS G1T textures to PNG for inspection: peek_tex.py <entry> [tex ...] -> extract/peek/<entry>_t<i>.png"""
import sys
from pathlib import Path
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "extract/peek"
OUT.mkdir(parents=True, exist_ok=True)
e = int(sys.argv[1])
d = Archive(sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].isdigit() else "CHS").read(e)
g = parse(d)
want = [int(x) for x in sys.argv[2:] if x.isdigit()] or range(len(g["tex"]))
for i in want:
    t = g["tex"][i]
    im = decode(d, t)
    bg = Image.new("RGBA", im.size, (40, 44, 60, 255))
    bg.alpha_composite(im)
    s = min(1.0, 1400 / max(im.size))
    bg.resize((max(1, int(im.width * s)), max(1, int(im.height * s)))).save(OUT / f"{e:05d}_t{i}.png")
    print(i, t["w"], t["h"], hex(t["fmt"]), "bbox", im.getchannel("A").getbbox())

"""peek_crop.py <entry> <tex> x0 y0 x1 y1 [scale] -> extract/peek/crop.png (RGB over dark) + crop_a.png (alpha)"""
import sys
from pathlib import Path
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
e, ti, x0, y0, x1, y1 = map(int, sys.argv[1:7])
s = float(sys.argv[7]) if len(sys.argv) > 7 else 3
d = Archive("CHS").read(e)
im = decode(d, parse(d)["tex"][ti]).crop((x0, y0, x1, y1))
bg = Image.new("RGBA", im.size, (40, 44, 60, 255))
bg.alpha_composite(im)
sz = (int(im.width * s), int(im.height * s))
bg.resize(sz, Image.Resampling.NEAREST).save(ROOT / "extract/peek/crop.png")
im.getchannel("A").resize(sz, Image.Resampling.NEAREST).save(ROOT / "extract/peek/crop_a.png")

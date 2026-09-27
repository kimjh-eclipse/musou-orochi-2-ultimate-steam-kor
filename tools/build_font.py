"""Draw the Korean charset into the CHS font atlas (entry 38) cells of their donor codes.

Only donor cells change: alpha half re-encoded from the new 48x48 glyph, colour half set to white.
Returns the new decompressed G1T bytes; writes a preview sheet and report.
"""
import json, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from bc3 import write_cell_alpha, block_offset
from ko_charset import table_codes

ROOT = Path(__file__).resolve().parents[1]
VF = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
FALLBACK = [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\seguisym.ttf"]
SIZE, WEIGHT = 47, "Medium"
WHITE = bytes.fromhex("ffffffff00000000")


def fonts():
    f = ImageFont.truetype(VF, SIZE)
    f.set_variation_by_name(WEIGHT)
    return [f] + [ImageFont.truetype(p, SIZE - 4) for p in FALLBACK]


def has_glyph(font, ch):
    try:
        return font.getmask(ch).getbbox() is not None
    except Exception:
        return False


def render(ch, fl):
    font = next((f for f in fl if has_glyph(f, ch)), None)
    if font is None:
        raise ValueError(f"no font has {ch!r}")
    size = font.size
    while True:
        # draw on a larger canvas so clipping at the cell edge is detectable, then crop to the cell
        g = Image.new("L", (64, 64), 0)
        f = font
        if size != font.size:
            f = font.font_variant(size=size)
            if font.path == VF:
                f.set_variation_by_name(WEIGHT)
        ImageDraw.Draw(g).text((32, 32), ch, font=f, fill=255, anchor="mm")
        a = np.asarray(g)
        ys, xs = np.nonzero(a)
        box = (int(xs.min()) - 8, int(ys.min()) - 8, int(xs.max()) - 8, int(ys.max()) - 8)
        if box[0] >= 1 and box[1] >= 1 and box[2] <= 46 and box[3] <= 46:
            return a[8:56, 8:56].copy(), box
        size -= 1


def build(g1t: bytes, charset: dict):
    codes = table_codes()
    cell_of = {c: k for k, c in enumerate(codes)}  # atlas cell k = table[k+1]
    buf = bytearray(g1t)
    fl = fonts()
    boxes = {}
    for ch, h in charset.items():
        k = cell_of[int(h, 16)]
        a, box = render(ch, fl)
        boxes[ch] = box
        cx, cy = k % 85, k // 85
        write_cell_alpha(buf, cx, cy, a)
        for by in range(12):
            for bx in range(12):
                o = block_offset(cx * 12 + bx, cy * 12 + by)
                buf[o + 8:o + 16] = WHITE
    b = np.array(list(boxes.values()))
    rep = {"glyphs": len(boxes), "font": VF, "size": SIZE, "weight": WEIGHT,
           "ink_box_min": b.min(axis=0).tolist(), "ink_box_max": b.max(axis=0).tolist(),
           "out_of_cell": [c for c, (l, t, r, bt) in boxes.items() if l < 0 or t < 0 or r > 47 or bt > 47]}
    return bytes(buf), rep


if __name__ == "__main__":
    from pc_idx import Archive
    from font_grid import W, H
    charset = json.loads((ROOT / "mapping/ko_charset.json").read_text(encoding="utf-8"))["chars"]
    new, rep = build(Archive("CHS").read(38), charset)
    print(rep)
    img = Image.frombytes("RGBA", (W, H), new[0x38:0x38 + W * H], "bcn", 3).getchannel("A")
    img.crop((0, 0, 48 * 20, 48 * 4)).save(ROOT / "extract/probe/ko_font_preview.png")

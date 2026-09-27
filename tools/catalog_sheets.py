"""Contact sheets of every localized CHS texture (cropped to alpha bbox), 12 per sheet, labelled entry/tex/size.
Output extract/catalog/sheet_###.png and index.json (sheet -> [(entry, tex)])."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "extract/catalog"
OUT.mkdir(parents=True, exist_ok=True)
rows = [json.loads(l) for l in (ROOT / "extract/image_textures.jsonl").open()]
chs = Archive("CHS")
CW, CH, COLS, PER = 520, 300, 3, 12
index, sheet, items, cache = {}, None, [], {}


def flush(n, items):
    if not items:
        return
    img = Image.new("RGBA", (CW * COLS, CH * ((len(items) + COLS - 1) // COLS)), (46, 50, 66, 255))
    dr = ImageDraw.Draw(img)
    for k, (lab, im) in enumerate(items):
        x, y = (k % COLS) * CW, (k // COLS) * CH
        im.thumbnail((CW - 8, CH - 26))
        img.alpha_composite(im, (x + 4, y + 22))
        dr.text((x + 4, y + 4), lab, fill=(255, 255, 0, 255))
    img.save(OUT / f"sheet_{n:03d}.png")


n = 0
for r in rows:
    e, ti = r["entry"], r["tex"]
    if e not in cache:
        cache = {e: chs.read(e)}
    d = cache[e]
    t = parse(d)["tex"][ti]
    try:
        im = decode(d, t)
    except Exception:
        continue
    a = im.getchannel("A")
    bb = a.point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0, im.width, im.height)
    im = im.crop(bb)
    bg = Image.new("RGBA", im.size, (46, 50, 66, 255))
    bg.alpha_composite(im)
    items.append((f"{e} t{ti} {t['w']}x{t['h']} f{t['fmt']:#x}", bg))
    index.setdefault(n, []).append([e, ti])
    if len(items) == PER:
        flush(n, items)
        items, n = [], n + 1
flush(n, items)
(OUT / "index.json").write_text(json.dumps(index), encoding="utf-8")
print("sheets", n + 1)

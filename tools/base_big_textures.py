"""Contact sheets of large (>=1024 wide) textures in the base archives 000-003, to locate language
screens that live outside the language files (e.g. the boot legal notice)."""
from pathlib import Path
from PIL import Image, ImageDraw
from pc_idx import Archive, used_ids
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "extract/base_big"
OUT.mkdir(parents=True, exist_ok=True)
items, n = [], 0


def flush():
    global items, n
    if not items:
        return
    sheet = Image.new("RGB", (4 * 330, ((len(items) + 3) // 4) * 200), (46, 50, 66))
    dr = ImageDraw.Draw(sheet)
    for k, (lab, im) in enumerate(items):
        x, y = (k % 4) * 330, (k // 4) * 200
        im.thumbnail((320, 176))
        sheet.paste(im.convert("RGB"), (x + 4, y + 20))
        dr.text((x + 4, y + 4), lab, fill=(255, 255, 0))
    sheet.save(OUT / f"base_{n:03d}.png")
    items, n = [], n + 1


for part in ("000", "001", "002", "003"):
    a = Archive(part)
    for e in used_ids(a.idx):
        if a.idx[e][1] < 1 << 20:
            continue
        try:
            d = a.read(e)
        except Exception:
            continue
        if d[:4] != b"GT1G":
            continue
        try:
            g = parse(d)
        except Exception:
            continue
        for t in g["tex"]:
            if t["w"] < 1024:
                continue
            try:
                im = decode(d, t)
            except Exception:
                continue
            items.append((f"{part}:{e} t{t['i']} {t['w']}x{t['h']} f{t['fmt']:#x}", im))
            if len(items) == 16:
                flush()
flush()
print("sheets", n)

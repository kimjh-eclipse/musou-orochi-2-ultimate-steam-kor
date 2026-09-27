"""Survey language G1T entries: formats, sizes, CHS-vs-JPN difference; write a contact sheet per entry."""
import collections, json
from pathlib import Path
from PIL import Image, ImageDraw
from pc_idx import Archive, used_ids
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "extract/images_chs"
OUT.mkdir(parents=True, exist_ok=True)
chs, jpn = Archive("CHS"), Archive("JPN")
fmts, rows = collections.Counter(), []
for e in used_ids(chs.idx):
    if e == 38:
        continue
    d = chs.read(e)
    if d[:4] != b"GT1G":
        continue
    g = parse(d)
    same = chs.raw(e) == jpn.raw(e)
    for t in g["tex"]:
        fmts[hex(t["fmt"])] += 1
    rows.append({"entry": e, "count": g["count"], "size": len(d), "same_as_jpn": same,
                 "tex": [(t["fmt"], t["w"], t["h"]) for t in g["tex"]]})
    if same:
        continue
    thumbs = []
    for t in g["tex"][:64]:
        try:
            im = decode(d, t)
        except Exception:
            continue
        im.thumbnail((256, 128))
        thumbs.append((t, im))
    if thumbs:
        cols = 4
        sheet = Image.new("RGBA", (cols * 264, ((len(thumbs) + cols - 1) // cols) * 150), (60, 60, 70, 255))
        dr = ImageDraw.Draw(sheet)
        for k, (t, im) in enumerate(thumbs):
            x, y = (k % cols) * 264, (k // cols) * 150
            sheet.alpha_composite(im, (x + 4, y + 2))
            dr.text((x + 4, y + 134), f"t{t['i']} {t['w']}x{t['h']} f{t['fmt']:#x}", fill="white")
        sheet.save(OUT / f"{e:05d}.png")
print("G1T entries", len(rows), "differ from JPN", sum(not r["same_as_jpn"] for r in rows))
print("formats", fmts.most_common())
(ROOT / "extract/images_survey.json").write_text(json.dumps(rows), encoding="utf-8")
big = sorted((r for r in rows if not r["same_as_jpn"]), key=lambda r: -r["size"])[:15]
for r in big:
    print(r["entry"], r["count"], r["size"], r["tex"][:3])

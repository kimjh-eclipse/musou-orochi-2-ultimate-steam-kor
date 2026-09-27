"""Find localized textures whose label layout resembles a reference texture (row count and relative widths)."""
import json, sys
from pathlib import Path
import numpy as np
from pc_idx import Archive
from g1t_pc import parse, decode
from label_boxes import boxes

ROOT = Path(__file__).resolve().parents[1]
ref_e, ref_t = int(sys.argv[1]), int(sys.argv[2])
chs = Archive("CHS")


def rows_of(im):
    bx = boxes(np.asarray(im.getchannel("A")), gap=3.0)
    return [b for b in bx if b[3] - b[1] > 8]


def sig(bx):
    w = np.array([b[2] - b[0] for b in bx], float)
    return w / w.max()


d = chs.read(ref_e)
ref = rows_of(decode(d, parse(d)["tex"][ref_t]))
rs = sig(ref)
hits = []
cache = {}
for l in (ROOT / "extract/image_textures.jsonl").open():
    r = json.loads(l)
    e, ti = r["entry"], r["tex"]
    if r.get("error"):
        continue
    if e not in cache:
        cache.clear()
        cache[e] = chs.read(e)
    d = cache[e]
    t = parse(d)["tex"][ti]
    try:
        bx = rows_of(decode(d, t))
    except Exception:
        continue
    if abs(len(bx) - len(ref)) <= 1 and len(bx) >= 3:
        n = min(len(bx), len(ref))
        err = float(np.abs(sig(bx)[:n] - rs[:n]).mean())
        hits.append((err, e, ti, t["w"], t["h"], len(bx)))
hits.sort()
for h in hits[:25]:
    print(f"err {h[0]:.3f} entry {h[1]} t{h[2]} {h[3]}x{h[4]} rows {h[5]}")

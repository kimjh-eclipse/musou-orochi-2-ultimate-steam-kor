"""Name atlases packed in their own order (6051 t5/t6). Shape matching against 6054 was not reliable
(제갈량/제갈탄, 하후연/하후패 ...), so the character index k of every box (boxes(gap=0.2), row-major) was
read off numbered tiles made with box_index_view.py."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load
from spec_names import NAME

ROOT = Path(__file__).resolve().parents[1]
K = {5: [93, 105, 88, 91, 97, 100, 101, 69, 77, 79, 80, 83, 98, 104, 61, 65, 66, 67, 68, 7, 70,
         73, 74, 75, 81, 84, 85, 87, 44, 89, 92, 95, 96, 102, 13, 106, 17, 39, 51, 72, 78, 3, 94, 42, 43, 11,
         46, 47, 49, 50, 52, 55, 59, 15, 18, 36, 20, 37, 10, 23, 86, 26, 2, 27, 0, 99, 31, 103, 19, 35, 40,
         21, 76, 8, 53, 9, 54, 41, 82, 24, 25, 56, 48, 28, 60, 34, 29, 30, 4, 12, 14, 5, 6, 62, 33, 71, 64,
         45, 57, 58, 16, 38, 63, 32, 1, 22, 90],
     6: [127, 129, 119, 143, 107, 116, 144, 115, 118, 131, 133, 140, 121, 126, 132, 124, 137, 111, 128, 112,
         138, 117, 109, 130, 125, 120, 134, 135, 136, 122, 141, 142, 123, 139, 114, 113, 108, 110]}
spec = []
for ti, ks in K.items():
    d, t, im = load(6051, ti)
    bx = boxes(np.asarray(im.getchannel("A")), gap=0.2)
    assert len(bx) == len(ks), (ti, len(bx), len(ks))
    labels = []
    for b, k in zip(bx, ks):
        nxt = [c for c in bx if abs(c[1] - b[1]) < 12 and c[0] > b[2]]
        right = min(c[0] for c in nxt) - 4 if nxt else t["w"] - 4
        labels.append({"box": b, "ko": NAME[k], "first_big": True, "extend_w": right - b[0], "pad": 0})
    spec.append({"tex": ti, "labels": labels})
p = ROOT / "mapping/images/06051.json"
old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
keep = [x for x in old if x["tex"] not in K]
p.write_text(json.dumps({"entry": 6051, "textures": keep + spec}, ensure_ascii=False), encoding="utf-8")
print({ti: len(v) for ti, v in K.items()}, "dupes t5", len(K[5]) - len(set(K[5])), "t6", len(K[6]) - len(set(K[6])))

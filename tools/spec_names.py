"""Character-name atlases. Grids follow the playable-character order k of entry 33 section 5
(0 夏侯惇 .. 144 ソフィーティア); boxes() returns them row-major. 6055 t3 mixes item art (first box, skipped)
with names in its own order (read off the texture)."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
NAME = {r["path"][1]: r["ko"].replace("　", " ") for r in rows if r["entry"] == 33 and r["path"][0] == 5 and r.get("ko")}
T3 = [127, 128, 129, 130, 131, 125, 126,
      135, 136, 137, 138, 139, 132, 133, 134,
      143, 144, 118, 119, 120, 140, 141, 142,
      124, 114, 115, 116, 117, 121, 122, 123]
JOBS = {(6054, 0): (0, list(range(0, 110))), (6054, 1): (0, list(range(110, 137))), (6054, 2): (0, list(range(137, 145))),
        (6055, 2): (0, list(range(0, 114))), (6055, 3): (1, T3),
        (6068, 6): (0, list(range(0, 45))), (6068, 7): (0, list(range(45, 90))), (6068, 8): (0, list(range(90, 135))),
        (6068, 9): (0, list(range(135, 145)))}
spec = {}
for (e, ti), (skip, ks) in JOBS.items():
    d, t, im = load(e, ti)
    bx = boxes(np.asarray(im.getchannel("A")))[skip:]
    assert len(bx) == len(ks), (e, ti, len(bx), len(ks))
    labels = []
    for i, (b, k) in enumerate(zip(bx, ks)):
        nxt = [c for c in bx if abs(c[1] - b[1]) < 20 and c[0] > b[2]]
        right = min(c[0] for c in nxt) - 8 if nxt else min(t["w"] - 4, b[0] + int((b[2] - b[0] + 1) * 1.8))
        labels.append({"box": b, "ko": NAME[k], "first_big": True, "extend_w": right - b[0], "pad": 1})
    spec.setdefault(e, []).append({"tex": ti, "labels": labels})
for e, texs in spec.items():
    p = ROOT / f"mapping/images/{e:05d}.json"
    old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
    keep = [x for x in old if x["tex"] not in {y["tex"] for y in texs}]
    p.write_text(json.dumps({"entry": e, "textures": keep + texs}, ensure_ascii=False), encoding="utf-8")
print({e: [len(x["labels"]) for x in v] for e, v in spec.items()})

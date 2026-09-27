"""Stage / event / location title textures (mapping/title_map.json from map_titles_offset.py) -> label specs.
One caption per texture: box = alpha bbox of the CHS art, first syllable drawn large like the originals."""
import json
from pathlib import Path
import numpy as np
from label_boxes import load

ROOT = Path(__file__).resolve().parents[1]
m = json.loads((ROOT / "mapping/title_map.json").read_text(encoding="utf-8"))
by_entry = {}
for x in m:
    d, t, im = load(x["pc_entry"], x["pc_tex"])
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 12)
    box = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    lab = {"box": box, "ko": x["ko"].replace("　", " "), "first_big": True,
           "extend_w": min(t["w"] - box[0] - 6, int((box[2] - box[0] + 1) * 1.8)), "pad": 0}
    by_entry.setdefault(x["pc_entry"], []).append({"tex": x["pc_tex"], "labels": [lab]})
for e, texs in by_entry.items():
    (ROOT / f"mapping/images/{e:05d}.json").write_text(json.dumps({"entry": e, "textures": texs}, ensure_ascii=False),
                                                      encoding="utf-8")
print("title specs", len(by_entry), sum(len(v) for v in by_entry.values()))

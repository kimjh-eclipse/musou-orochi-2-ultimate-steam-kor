"""PC stage/event title entry -> PS3 v19 catalog entry by the id offsets found with match_ps3_titles.py.

PC 4532-4890 = PS3 +283, PC 4891-4958 = PS3 +357, PC 13554-13910 = PS3 +1176 (runs of 25+160+56+130 matches).
Each pair is re-scored (same signature as the matcher) and written to mapping/title_map.json.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode
from match_ps3_titles import sig, ROOT, V19

RANGES = [(4532, 4890, 283), (4891, 4958, 357), (13554, 13910, 1176)]
AUDIT = ROOT.parent / "work_wo3u/jp_story_v18/titles_audit"
cat = {t["entry"]: t for t in json.loads((V19 / "catalog.json").read_text(encoding="utf-8"))["targets"]}
rows = [json.loads(l) for l in (ROOT / "extract/image_textures.jsonl").open(encoding="utf-8")]
jpn = Archive("JPN")
out, miss = [], []
for r in rows:
    e = r["entry"]
    off = next((o for a, b, o in RANGES if a <= e <= b), None)
    if off is None:
        continue
    t = cat.get(e + off)
    if t is None:
        miss.append((e, r["tex"], e + off, "not in ps3 catalog"))
        continue
    d = jpn.read(e)
    tex = parse(d)["tex"][r["tex"]]
    s, asp = sig(np.asarray(decode(d, tex))[..., 3])
    a = np.asarray(Image.open(AUDIT / f"{t['entry']}_{t['texture']}.png").convert("RGBA"))[..., 3]
    x0, y0, x1, y1 = t["bbox"]
    s2, asp2 = sig(a[y0:y1 + 1, x0:x1 + 1])
    sc = float(s @ s2) if s is not None else -1
    out.append({"pc_entry": e, "pc_tex": r["tex"], "size": [tex["w"], tex["h"]], "ps3_entry": t["entry"],
                "source": t["source"], "ko": t["ko"], "family": t["family"], "score": round(sc, 3)})
(ROOT / "mapping/title_map.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print("mapped", len(out), "low(<0.9)", [(o["pc_entry"], o["source"], o["score"]) for o in out if o["score"] < 0.9])
print("miss", miss)

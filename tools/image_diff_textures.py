"""Per-texture CHS vs JPN comparison for language G1T entries -> extract/image_textures.jsonl.
A texture is 'localized' when decoded pixels differ; records size, format and changed-pixel bbox."""
import json
from pathlib import Path
import numpy as np
from pc_idx import Archive, used_ids
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
chs, jpn = Archive("CHS"), Archive("JPN")
out = []
tot = 0
for e in used_ids(chs.idx):
    if e == 38 or chs.raw(e) == jpn.raw(e):
        continue
    a, b = chs.read(e), jpn.read(e)
    if a[:4] != b"GT1G":
        continue
    ga, gb = parse(a), parse(b)
    for t in ga["tex"]:
        tb = gb["tex"][t["i"]] if t["i"] < gb["count"] else None
        rec = {"entry": e, "tex": t["i"], "fmt": t["fmt"], "w": t["w"], "h": t["h"]}
        try:
            ia = np.asarray(decode(a, t))
        except Exception as err:
            rec["error"] = str(err)
            out.append(rec)
            continue
        if tb is None or (tb["w"], tb["h"]) != (t["w"], t["h"]):
            rec["diff"] = "layout"
        else:
            ib = np.asarray(decode(b, tb))
            m = (np.abs(ia.astype(int) - ib.astype(int)).max(axis=2) > 24)
            if not m.any():
                continue
            ys, xs = np.nonzero(m)
            rec.update(diff="pixels", changed=int(m.sum()), bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
        out.append(rec)
        tot += 1
with (ROOT / "extract/image_textures.jsonl").open("w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
import collections
print("localized textures", tot, "in entries", len({r["entry"] for r in out}))
print(collections.Counter(r.get("diff", "err") for r in out))
print("errors", [r for r in out if "error" in r][:5])

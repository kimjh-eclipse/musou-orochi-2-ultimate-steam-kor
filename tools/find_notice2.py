"""Legal notice search, alpha-aware: localized CHS textures holding opaque pure-red ink AND opaque white ink."""
import json
from pathlib import Path
import numpy as np
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
chs = Archive("CHS")
cache = {}
for l in (ROOT / "extract/image_textures.jsonl").open():
    r = json.loads(l)
    e, ti = r["entry"], r["tex"]
    if e not in cache:
        cache = {e: chs.read(e)}
    d = cache[e]
    t = parse(d)["tex"][ti]
    try:
        a = np.asarray(decode(d, t)).astype(int)
    except Exception:
        continue
    op = a[..., 3] > 200
    if op.sum() < 500:
        continue
    red = (op & (a[..., 0] > 190) & (a[..., 1] < 50) & (a[..., 2] < 50)).sum()
    white = (op & (a[..., :3].min(axis=2) > 220)).sum()
    if red > 300 and white > 3000:
        print(f"{e} t{ti} {t['w']}x{t['h']} fmt {t['fmt']:#x} red {red} white {white}", flush=True)
print("done")

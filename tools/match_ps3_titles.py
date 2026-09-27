"""Match PC localized title textures (JPN slot, same ids as CHS) to the PS3 v19 title catalog by image similarity.

PS3 originals: work_wo3u/jp_story_v18/titles_audit/<entry>_<tex>.png (Japanese source art) + catalog.json (source, ko).
PC candidates: every texture listed in extract/image_textures.jsonl, decoded from the JPN archive.
Signature: alpha cropped to its bbox, resized to 96x24, zero-mean unit-norm; plus bbox aspect.
Writes mapping/ps3_title_match.json: [{pc_entry, pc_tex, ps3_entry, ps3_tex, source, ko, score, second}]
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]
V19 = ROOT.parent / "work_wo3u/jp_titles_v19"
SW, SH = 96, 24


def sig(alpha):
    im = Image.fromarray(alpha)
    bb = im.getbbox()
    if not bb:
        return None, 0
    c = im.crop(bb).resize((SW, SH), Image.Resampling.BILINEAR)
    v = np.asarray(c, np.float32).ravel()
    v -= v.mean()
    n = np.linalg.norm(v)
    return (v / n if n else v), (bb[2] - bb[0]) / max(1, bb[3] - bb[1])


if __name__ == "__main__":
    cat = json.loads((V19 / "catalog.json").read_text(encoding="utf-8"))["targets"]
    ps3 = []
    for t in cat:
        p = ROOT.parent / "work_wo3u/jp_story_v18/titles_audit" / f"{t['entry']}_{t['texture']}.png"
        if not p.exists():
            continue
        a = np.asarray(Image.open(p).convert("RGBA"))[..., 3]
        x0, y0, x1, y1 = t["bbox"]
        s, asp = sig(a[y0:y1 + 1, x0:x1 + 1])
        if s is not None:
            ps3.append((t, s, asp))
    print("ps3 signatures", len(ps3), "of", len(cat))

    rows = [json.loads(l) for l in (ROOT / "extract/image_textures.jsonl").open(encoding="utf-8")]
    jpn = Archive("JPN")
    cache = {}
    out = []
    S = np.stack([s for _, s, _ in ps3])
    A = np.array([a for _, _, a in ps3])
    for r in rows:
        e, ti = r["entry"], r["tex"]
        if e not in cache:
            try:
                d = jpn.read(e)
                cache.clear()
                cache[e] = (d, parse(d))
            except Exception:
                continue
        d, g = cache[e]
        if ti >= len(g["tex"]):
            continue
        t = g["tex"][ti]
        if t["w"] * t["h"] > 1024 * 512:
            continue
        a = np.asarray(decode(d, t))[..., 3]
        s, asp = sig(a)
        if s is None:
            continue
        sc = S @ s - 0.15 * np.abs(np.log(A / asp))
        o = np.argsort(-sc)
        best, second = int(o[0]), int(o[1])
        tt = ps3[best][0]
        out.append({"pc_entry": e, "pc_tex": ti, "size": [t["w"], t["h"]], "ps3_entry": tt["entry"], "ps3_tex": tt["texture"],
                    "source": tt["source"], "ko": tt["ko"], "family": tt["family"],
                    "score": round(float(sc[best]), 3), "second": round(float(sc[second]), 3),
                    "second_source": ps3[second][0]["source"]})
    (ROOT / "mapping/ps3_title_match.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    good = [m for m in out if m["score"] > 0.8]
    print("pc textures", len(out), "score>0.8", len(good))

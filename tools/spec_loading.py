"""Loading-screen name cards: entries 207+6k and 208+6k show playable character k (entry 33 section 5 order,
k = 0 夏侯惇 .. 144 ソフィーティア). Korean names come from the PS3 v27 translation (full-width space -> space)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
names = {r["path"][1]: r["ko"] for r in rows if r["entry"] == 33 and r["path"][0] == 5 and r.get("ko")}
listed = {(json.loads(l)["entry"], json.loads(l)["tex"]) for l in (ROOT / "extract/image_textures.jsonl").open(encoding="utf-8")}
n = 0
for k in range(145):
    ko = names[k].replace("　", " ")
    for e in (207 + 6 * k, 208 + 6 * k):
        assert (e, 0) in listed, (e, k)
        spec = {"entry": e, "textures": [{"tex": 0, "overpaint": {"region": [0, 700, 1400, 1080], "ko": ko}}]}
        (ROOT / f"mapping/images/{e:05d}.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        n += 1
print("loading specs", n)

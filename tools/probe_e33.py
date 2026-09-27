import collections, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
e33 = [r for r in rows if r["entry"] == 33]
print("PC 33 strings", len(e33), "paired ps3", {r["ps3_entry"] for r in e33}, collections.Counter(r["level"] for r in e33))
secs = collections.Counter((r["path"][0], r["level"]) for r in e33)
print(sorted(secs.items()))
for r in [r for r in e33 if r["level"] == "untranslated_ps3"][:8]:
    print("  ", r["path"], r["jp"][:40].replace("\n", "/"))
tm = [json.loads(l) for l in (ROOT / "translation_memory/ps3_tm.jsonl").open(encoding="utf-8")]
cnt = collections.Counter((r["ps3_entry"], r["changed"]) for r in tm if r["ps3_entry"] in (33, 34, 35, 36))
print("PS3 33-36 changed counts", sorted(cnt.items()))
# where else does a sample untranslated string occur in PS3, translated?
sample = [r for r in e33 if r["level"] == "untranslated_ps3"][100]["jp"]
hits = [(r["ps3_entry"], r["path"], r["changed"], r["ko"][:30]) for r in tm if r["jp"] == sample]
print("sample", sample[:40], hits[:10])

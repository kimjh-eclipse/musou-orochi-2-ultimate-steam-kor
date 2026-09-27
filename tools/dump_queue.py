"""Dump unique untranslated JP strings of a batch for manual translation.

ESC is written as ⟨E⟩ so control codes stay visible; translations use the same notation.
Batches: A = entry 33 sections 0,1,2,3,4,6 + DLC/other entries; B = entry 33 section 5 real text;
C = placeholders (予備/ダミー/説明文/...).
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PH = re.compile(r"(予備|ダミー|説明文|^コスチューム\d|^ＤＬＣ)")
ver, batch = sys.argv[1], sys.argv[2]
q = [json.loads(l) for l in (ROOT / f"build/{ver}/untranslated_queue.jsonl").open(encoding="utf-8")]
done = set()
for p in (ROOT / "translation_memory").glob("pc_ko_*.jsonl"):
    for l in p.open(encoding="utf-8"):
        if l.strip():
            done.add(json.loads(l)["jp"])


def batch_of(r):
    if PH.search(r["jp"]):
        return "C"
    if r["entry"] == 33 and r["path"][0] == 5:
        return "B"
    return "A"


seen, rows = set(), []
for r in q:
    if batch_of(r) != batch or r["jp"] in seen or r["jp"] in done:
        continue
    seen.add(r["jp"])
    rows.append({"n": len(rows), "entry": r["entry"], "path": r["path"], "jp": r["jp"].replace("\x1b", "⟨E⟩")})
out = ROOT / "translation_memory" / f"queue_{batch}.jsonl"
with out.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(batch, len(rows), "unique ->", out)

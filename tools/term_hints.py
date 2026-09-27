"""Print PS3 glossary hits (short translated terms contained in each queued string) for a range of queue items."""
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
batch, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
terms = collections.defaultdict(collections.Counter)
for l in (ROOT / "translation_memory/ps3_tm.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    j = r["jp"]
    if r["changed"] and 2 <= len(j) <= 12 and "\n" not in j and "\x1b" not in j:
        terms[j][r["ko"]] += 1
best = {j: c.most_common(1)[0][0] for j, c in terms.items()}
keys = sorted(best, key=len, reverse=True)
for l in (ROOT / f"translation_memory/queue_{batch}.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    if not lo <= r["n"] < hi:
        continue
    s = r["jp"]
    hits = []
    for k in keys:
        if k in s and not any(k in h for h, _ in hits):
            hits.append((k, best[k]))
        if len(hits) >= 6:
            break
    if hits:
        print(r["n"], " | ".join(f"{a}={b}" for a, b in hits))

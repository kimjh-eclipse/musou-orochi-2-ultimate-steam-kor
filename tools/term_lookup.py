"""Look up how PS3 rendered given JP terms: exact rows first, then short rows containing the term."""
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
words = sys.argv[1:]
exact = collections.defaultdict(collections.Counter)
near = collections.defaultdict(collections.Counter)
for l in (ROOT / "translation_memory/ps3_tm.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    if not r["changed"]:
        continue
    for w in words:
        if r["jp"] == w:
            exact[w][r["ko"]] += 1
        elif w in r["jp"] and len(r["jp"]) <= len(w) + 8:
            near[w][(r["jp"], r["ko"])] += 1
for w in words:
    e = exact[w].most_common(3)
    n = [f"{a}={b}" for (a, b), _ in near[w].most_common(3)]
    print(w, "::", e if e else "-", "||", " ; ".join(n)[:220].replace("\n", "/"))

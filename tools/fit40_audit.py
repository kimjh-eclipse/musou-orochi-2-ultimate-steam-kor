"""Audit fit40 outputs beyond fit40_check: text inside colour codes unchanged, and each new line still resembles
its own old line (catches rows written against the wrong id). usage: fit40_audit.py [XX ...]"""
import json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
PARTS = Path(__file__).resolve().parents[1] / "translation_memory/fit40_parts"
CODED = re.compile(r"⟨E⟩(?:[AC][0-9]|P.)(.*?)⟨E⟩R")


def bigrams(s):
    s = re.sub(r"⟨E⟩(?:[AC][0-9]|P.|R)|[\s.,!?…~]", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def audit(k):
    src = {r["id"]: r for r in map(json.loads, (PARTS / f"in_{k}.jsonl").open(encoding="utf-8"))}
    out = [json.loads(l) for l in (PARTS / f"out_{k}.jsonl").open(encoding="utf-8") if l.strip()]
    bad = 0
    for r in out:
        old, new = src[r["id"]]["ko"], r["ko"]
        if CODED.findall(old) != CODED.findall(new):
            print(f"  {k}/{r['id']} coded text changed: {CODED.findall(old)} -> {CODED.findall(new)}"); bad += 1
        a, b = bigrams(old), bigrams(new)
        sim = len(a & b) / max(1, len(b))
        # compare against neighbours: a misplaced row matches a neighbour better than its own source
        best = max(((len(bigrams(src[j]["ko"]) & b) / max(1, len(b)), j) for j in (r["id"] - 3, r["id"] - 2, r["id"] - 1,
                    r["id"] + 1, r["id"] + 2, r["id"] + 3) if j in src), default=(0, None))
        if sim < 0.35 or best[0] > sim:
            print(f"  {k}/{r['id']} low similarity {sim:.2f} (neighbour {best[1]} {best[0]:.2f})\n"
                  f"      OLD {old!r}\n      NEW {new!r}"); bad += 1
    print(f"part {k}: {len(out)} rows, {bad} flagged")


for k in sys.argv[1:] or sorted(p.stem[4:] for p in PARTS.glob("out_*.jsonl")):
    audit(k)

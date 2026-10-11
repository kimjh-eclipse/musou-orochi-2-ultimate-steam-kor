"""Check hand-shortened live mission messages: usage  msg22_check.py <part.jsonl> <answer.jsonl>
part rows: {"key", "jp", "ko", "orig_ko", "cells"} (from msg22_left.jsonl); answer rows: {"key": [...], "ko": "..."}
Rules as gen_ko_R_msg22.check, compared against orig_ko. Prints each problem; exit 1 if any.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from gen_ko_R_msg22 import check
from msg22_queue import ESC, cells

part = {json.dumps(r["key"]): r for r in map(json.loads, open(sys.argv[1], encoding="utf-8"))}
ans, bad = {}, []
for n, l in enumerate(open(sys.argv[2], encoding="utf-8"), 1):
    if not l.strip():
        continue
    a = json.loads(l)
    k = json.dumps(a["key"])
    if k not in part:
        bad.append((n, "unknown key", a["key"]))
    elif k in ans:
        bad.append((n, "duplicate key", a["key"]))
    ans[k] = a["ko"]
for k, r in part.items():
    if k not in ans:
        bad.append((k, "missing"))
        continue
    why = check(r["orig_ko"], ans[k])
    if why:
        bad.append((k, why, f"{cells(ans[k][2:])} cells", ESC.sub("^", ans[k])))
for b in bad:
    print("BAD", b)
print(f"{len(part)} rows, {len(ans)} answers, {len(bad)} problems")
sys.exit(1 if bad else 0)

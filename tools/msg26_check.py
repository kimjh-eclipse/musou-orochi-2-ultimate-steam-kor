"""Check shortened mission messages: usage  msg26_check.py <part.jsonl> <answers.jsonl>

part rows:    {"key", "jp", "ko", "glyphs"}         (from msg26_queue.jsonl)
answer rows:  {"key": [...], "ko": "<new Korean, full string incl. the 2-digit prefix>"}
Rules: every key answered once; same 2-digit prefix; same sequence of ESC colour codes (\x1b C<n> ... \x1b R) as the
current Korean; same %s count; no "\\n"; <= 26 glyphs (codes not counted, spaces counted, %s = 4); encodable.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from ko_encode import can_encode

ESC = re.compile(r"\x1b[A-Z][0-9A-Z]?")
LIMIT = 26


def glyphs(s):
    return len(ESC.sub("", s).replace("%s", "%%%%"))


def main():
    part = {json.dumps(r["key"]): r for r in map(json.loads, open(sys.argv[1], encoding="utf-8"))}
    ans = {}
    bad = []
    for n, l in enumerate(open(sys.argv[2], encoding="utf-8"), 1):
        if not l.strip():
            continue
        a = json.loads(l)
        k = json.dumps(a["key"])
        if k not in part:
            bad.append((n, "unknown key", a["key"]))
            continue
        if k in ans:
            bad.append((n, "duplicate key", a["key"]))
        ans[k] = a["ko"]
    for k, r in part.items():
        if k not in ans:
            bad.append((k, "missing"))
            continue
        ko, old = ans[k], r["ko"]
        why = []
        if ko[:2] != old[:2]:
            why.append("prefix")
        if ESC.findall(ko) != ESC.findall(old):
            why.append("colour codes differ")
        if ko.count("%s") != old.count("%s"):
            why.append("%s count")
        if "\\n" in ko or "\n" in ko:
            why.append("line break")
        g = glyphs(ko[2:])
        if g > LIMIT:
            why.append(f"{g} glyphs")
        if not can_encode(ESC.sub("", ko)):
            why.append("not encodable")
        if why:
            bad.append((k, why, ESC.sub("^", ko)))
    for b in bad:
        print("BAD", b)
    print(f"{len(part)} rows, {len(ans)} answers, {len(bad)} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

"""Split / check / merge the 40-glyph shortening work.

  fit40_check.py split <n>          translation_memory/fit40_queue.jsonl -> fit40_parts/in_XX.jsonl (ESC shown as ⟨E⟩)
  fit40_check.py check <XX>         validate fit40_parts/out_XX.jsonl against in_XX.jsonl
  fit40_check.py merge              all out_XX -> translation_memory/pc_ko_D_fit40.jsonl (build_text override, wins last)

Checks per row: every input id answered once; ESC code sequence, format tokens, leading 2-digit code and newline
count identical to the current Korean; rendered glyphs <= 40; encodable with the Korean charset; text changed.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit40_queue import glyphs, LIMIT, ESC, TOK
from ko_encode import can_encode

ROOT = Path(__file__).resolve().parents[1]
TM = ROOT / "translation_memory"
PARTS = TM / "fit40_parts"
E = "⟨E⟩"


def show(s):
    return s.replace("\x1b", E)


def real(s):
    return s.replace(E, "\x1b")


def shape(s):
    return (ESC.findall(s), TOK.findall(s), re.match(r"^\d\d(?=\D)", s) and s[:2], s.count("\n"), s.count("\\n"))


def split(n):
    q = [json.loads(l) for l in (TM / "fit40_queue.jsonl").open(encoding="utf-8")]
    PARTS.mkdir(exist_ok=True)
    size = -(-len(q) // n)
    for k in range(n):
        rows = q[k * size:(k + 1) * size]
        (PARTS / f"in_{k:02d}.jsonl").write_text("".join(
            json.dumps({"id": k * size + i, "jp": show(r["jp"]), "ko": show(r["ko"]), "glyphs": r["glyphs"],
                        "over": r["over"]}, ensure_ascii=False) + "\n" for i, r in enumerate(rows)), encoding="utf-8")
    print(len(q), "rows ->", n, "parts of", size)


def check(k, quiet=False):
    src = {r["id"]: r for r in map(json.loads, (PARTS / f"in_{k}.jsonl").open(encoding="utf-8"))}
    p = PARTS / f"out_{k}.jsonl"
    if not p.exists():
        print(f"part {k}: no output"); return False
    errs, seen = [], set()
    for ln, l in enumerate(p.open(encoding="utf-8"), 1):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except json.JSONDecodeError as e:
            errs.append(f"line {ln}: bad json {e}"); continue
        i = r.get("id")
        if i not in src:
            errs.append(f"line {ln}: unknown id {i}"); continue
        if i in seen:
            errs.append(f"id {i}: duplicate"); continue
        seen.add(i)
        old, new = real(src[i]["ko"]), real(r.get("ko", ""))
        if shape(new) != shape(old):
            errs.append(f"id {i}: codes/tokens/newlines differ: {shape(old)} vs {shape(new)}")
        g = glyphs(new)
        if g > LIMIT:
            errs.append(f"id {i}: {g} glyphs > {LIMIT}: {show(new)!r}")
        if not can_encode(new):
            bad = "".join(sorted({c for c in new if not can_encode(c)}))
            errs.append(f"id {i}: unencodable {bad!r}")
        if new == old:
            errs.append(f"id {i}: unchanged")
    missing = sorted(set(src) - seen)
    if missing:
        errs.append(f"missing ids ({len(missing)}): {missing[:20]}")
    if not quiet or errs:
        print(f"part {k}: {len(seen)}/{len(src)} rows, {len(errs)} errors")
        for e in errs[:60]:
            print("  ", e)
    return not errs


def merge():
    ins = sorted(PARTS.glob("in_*.jsonl"))
    ok = all(check(p.stem[3:], quiet=True) for p in ins)
    if not ok:
        sys.exit("fix errors before merging")
    rows = []
    for p in ins:
        k = p.stem[3:]
        src = {r["id"]: r for r in map(json.loads, p.open(encoding="utf-8"))}
        for l in (PARTS / f"out_{k}.jsonl").open(encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                rows.append({"jp": real(src[r["id"]]["jp"]), "ko": real(r["ko"])})
    (TM / "pc_ko_D_fit40.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print("merged", len(rows), "rows -> pc_ko_D_fit40.jsonl")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "split":
        split(int(sys.argv[2]))
    elif cmd == "check":
        sys.exit(0 if check(sys.argv[2]) else 1)
    elif cmd == "merge":
        merge()

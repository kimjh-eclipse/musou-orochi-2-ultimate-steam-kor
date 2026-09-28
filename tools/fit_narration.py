"""Story narration window (stage intro / 3-line narration, PC entry 53 and its copies in 34): limits and queue.

Measured on issue #4 (1장 동구구출전): the window draws at most 90 glyphs (newline and colour codes not counted,
spaces counted; Japanese lines are <= 30 characters x 3 lines). A line is wrapped by width: a 34-glyph Korean line
fit, a 38-glyph line wrapped after 36. A wrapped line pushes the text past 3 visual lines and the tail is cut.
Rule used here: total <= 90 glyphs, every line <= LINE_MAX glyphs, at most 3 lines (the window height).

usage: fit_narration.py            report
       fit_narration.py --queue    write translation_memory/fit90_queue.jsonl
"""
import collections, glob, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
ESC = re.compile(r"\x1b(?:[AC][0-9]|P.|R)")
TOTAL_MAX, LINE_MAX = 90, 34
KO_LEVELS = {"exact_path", "entry_text", "global_text", "conflict", "global_fill"}


def lines(s):
    return ESC.sub("", s).replace("\\n", "\n").split("\n")


def problems(jp, ko):
    kl, jl = lines(ko), lines(jp)
    out = []
    total = sum(len(x) for x in kl)
    if total > TOTAL_MAX:
        out.append(f"total {total}")
    long = [len(x) for x in kl if len(x) > LINE_MAX]
    if long:
        out.append(f"line {max(long)}")
    if len(kl) > max(3, len(jl)):
        out.append(f"lines {len(kl)}")
    return out


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    narration = {}   # jp -> ko for PC entry 53 strings
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r["entry"] == 53 and r["jp"]:
            ko = ov.get(r["jp"], r["ko"] if r["level"] in KO_LEVELS else None)
            if ko:
                narration[r["jp"]] = ko
    rows, cnt = [], collections.Counter()
    for jp, ko in narration.items():
        pr = problems(jp, ko)
        if pr:
            rows.append({"jp": jp, "ko": ko, "problems": pr})
            for p in pr:
                cnt[p.split()[0]] += 1
    jp_total = max(sum(len(x) for x in lines(j)) for j in narration)
    jp_line = max(max(len(x) for x in lines(j)) for j in narration)
    print(f"narration strings {len(narration)} (jp max total {jp_total}, max line {jp_line})")
    print(f"over limits: {len(rows)}  by kind {dict(cnt)}")
    if "--queue" in sys.argv:
        p = ROOT / "translation_memory/fit90_queue.jsonl"
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print("wrote", p)
    return rows


if __name__ == "__main__":
    main()

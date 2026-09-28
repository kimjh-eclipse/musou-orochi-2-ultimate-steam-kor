"""Per text table: how many Korean strings exceed the longest Japanese string of the same table
(total glyphs, longest line, line count). A window is laid out for its longest Japanese text, so Korean beyond
that is at risk of wrap / cut. Survey only; the table/part key is entry (and first path element for LX parts).
"""
import collections, glob, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
ESC = re.compile(r"\x1b(?:[AC][0-9]|P.|R)")
TOK = re.compile(r"%[0-9]*[sdwu]")
KO_LEVELS = {"exact_path", "entry_text", "global_text", "conflict", "global_fill"}


def shape(s):
    s = TOK.sub("xxxxxx", ESC.sub("", s)).replace("\\n", "\n")
    s = re.sub(r"^\d\d(?=\D)", "", s)
    ls = s.split("\n")
    return sum(len(x) for x in ls), max(len(x) for x in ls), len(ls)


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    groups = collections.defaultdict(list)
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"]
        if not jp:
            continue
        ko = ov.get(jp, r["ko"] if r["level"] in KO_LEVELS else None)
        if not ko:
            continue
        e = r["entry"]
        key = (e, r["path"][0]) if e == 33 or len(r["path"]) > 1 else (e,)
        if 63 <= e <= 260:
            key = ("char",)
        elif e > 260 and len(r["path"]) > 1:
            key = ("stage", r["path"][0])
        elif e > 260:
            key = (e,)
        groups[key].append((jp, ko))
    print(f"{'table':14} {'n':>6} {'jp max tot/line/lines':>22} {'ko over tot':>11} {'over line':>9} {'more lines':>10}")
    for key, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
        js = [shape(j) for j, _ in rows]
        mt, ml, mn = max(x[0] for x in js), max(x[1] for x in js), max(x[2] for x in js)
        ot = ol = on = 0
        for (j, k) in rows:
            t, li, n = shape(k)
            ot += t > mt
            ol += li > ml + 4          # Korean glyph/space mix: allow a small margin over the jp line length
            on += n > mn
        if (ot or ol or on) and len(rows) >= 30:
            print(f"{str(key):14} {len(rows):6} {f'{mt}/{ml}/{mn}':>22} {ot:11} {ol:9} {on:10}")


if __name__ == "__main__":
    main()

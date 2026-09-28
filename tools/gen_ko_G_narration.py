"""Fit the 3-line narration window (PC entries 53 and 6064; the same strings sit in 34): issue #4.

Window: at most 90 glyphs drawn (newline / colour codes not counted, spaces counted), 3 lines, a line wider than
~34-36 glyphs is wrapped by the game in the middle of a word and pushes the tail out of the window.
Fix: keep the translation, re-break the lines at word boundaries so every line is <= LINE_MAX glyphs (greedy fill,
at most 3 lines). Strings still over 90 glyphs need a shorter translation: SHORT[jp] (written by hand).

usage: gen_ko_G_narration.py            report
       gen_ko_G_narration.py --write    translation_memory/pc_ko_G_narration.jsonl
"""
import glob, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from ko_encode import can_encode

ESC = re.compile(r"\x1b(?:[AC][0-9]|P.|R)")
TOTAL_MAX, LINE_MAX, LINES = 90, 34, 3
KO_LEVELS = {"exact_path", "entry_text", "global_text", "conflict", "global_fill"}
ENTRIES = {53, 6064}
SHORT = {}   # jp -> shortened Korean (filled in from short_narration.json)
_short = ROOT / "translation_memory/short_narration.json"
if _short.exists():
    SHORT = json.loads(_short.read_text(encoding="utf-8"))


def vis(s):
    return len(ESC.sub("", s))


def ok(ko):
    ls = ko.split("\n")
    return len(ls) <= LINES and all(vis(x) <= LINE_MAX for x in ls) and sum(vis(x) for x in ls) <= TOTAL_MAX


def reflow(ko):
    """Choose the best line breaks among all ways to cut the words into <= 3 lines of <= LINE_MAX glyphs.
    Cost: a break at the translator's original position is free, after a sentence end is cheap, elsewhere
    expensive; plus unevenness of the line lengths (avoids one-word orphan lines)."""
    import itertools
    words, orig = [], set()
    for li, line in enumerate(ko.split("\n")):
        ws = [w for w in line.split(" ") if w]
        words += ws
        if li < ko.count("\n"):
            orig.add(len(words))          # original break after this many words
    n = len(words)
    best, best_cost = None, None
    for k in range(0, LINES):
        for cuts in itertools.combinations(range(1, n), k):
            bounds = (0,) + cuts + (n,)
            ls = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
            lens = [vis(x) for x in ls]
            if max(lens) > LINE_MAX:
                continue
            cost = 0.0
            for c in cuts:
                if c in orig:
                    cost += 0
                elif re.search(r"[.!?…」』]$", words[c - 1]):
                    cost += 4
                else:
                    cost += 12
            avg = sum(lens) / len(lens)
            cost += sum((x - avg) ** 2 for x in lens) / 20
            if best_cost is None or cost < best_cost:
                best, best_cost = "\n".join(ls), cost
    return best if best else greedy(ko)


def greedy(ko):
    """Greedy re-break at spaces; colour-coded names stay whole (a code never spans a break)."""
    words = ko.replace("\n", " ").split(" ")
    words = [w for w in words if w]
    lines, cur = [], ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if vis(cand) <= LINE_MAX:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return "\n".join(lines)


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_G_narration.jsonl":   # only the overrides applied before this one
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    strings = {}
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r["entry"] in ENTRIES and r["jp"]:
            ko = ov.get(r["jp"], r["ko"] if r["level"] in KO_LEVELS else None)
            if ko:
                strings[r["jp"]] = ko
    out, need_short = [], []
    for jp, ko in strings.items():
        if ok(ko) and jp not in SHORT:
            continue
        base = SHORT.get(jp, ko)
        new = base if ok(base) else reflow(base)
        if not ok(new):
            need_short.append((jp, ko, vis(ko.replace("\n", ""))))
            continue
        assert ESC.findall(new) == ESC.findall(ko) or jp in SHORT, jp
        assert can_encode(new), new
        out.append({"jp": jp, "ko": new})
    print(f"narration strings {len(strings)}; fixed by re-break or SHORT: {len(out)}; still need shortening: {len(need_short)}")
    for jp, ko, g in need_short:
        print(f"  [{g}] {ko!r}")
    if "--write" in sys.argv:
        if need_short:
            sys.exit("shorten the strings above first (translation_memory/short_narration.json)")
        p = ROOT / "translation_memory/pc_ko_G_narration.jsonl"
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
        print("wrote", p, len(out))


if __name__ == "__main__":
    main()

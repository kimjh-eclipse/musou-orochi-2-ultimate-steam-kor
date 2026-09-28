"""Queue battle-message strings whose Korean exceeds the 40-glyph message box limit.

In-battle message windows draw at most 40 glyphs (newline and ESC colour codes are not counted; spaces are).
Measured on screenshots of 5 cut lines (issue #1); every Japanese line in the per-character / per-stage
dialogue tables is <= 40 glyphs. Format tokens (%s) expand at runtime, so they are counted with TOKEN_W glyphs.

Output translation_memory/fit40_queue.jsonl: one row per unique Japanese string {jp, ko, glyphs, over, entries}.
The effective Korean is resolved the same way as build_text.py (pc_ko_* overrides win over PS3 matches).
"""
import collections, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 40
TOKEN_W = 6
ESC = re.compile(r"\x1b(?:[AC][0-9]|P.|R)")
TOK = re.compile(r"%(?:[0-9]*[sdwu])")
KO_LEVELS = {"exact_path", "entry_text", "global_text", "conflict", "global_fill"}
SKIP_ENTRIES = {33, 49, 53}  # UI / help / narration boxes, not the 40-glyph message window


def glyphs(s):
    """Rendered glyph count: ESC colour codes, the 2-digit message code prefix, newlines (real or literal
    backslash-n) are not drawn; each format token counts TOKEN_W glyphs."""
    s = ESC.sub("", s or "").replace("\\n", "\n")
    s = re.sub(r"^\d\d(?=\D)", "", s)
    n_tok = len(TOK.findall(s))
    return len(TOK.sub("", s).replace("\n", "")) + n_tok * TOKEN_W


def overrides():
    ov = {}
    for p in sorted((ROOT / "translation_memory").glob("pc_ko_*.jsonl")):
        for l in p.open(encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    return ov


def main():
    ov = overrides()
    rows = {}
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"]
        if not jp or r["entry"] in SKIP_ENTRIES:
            continue
        ko = ov.get(jp) or (r["ko"] if r["level"] in KO_LEVELS else None)
        if not ko or glyphs(jp) > LIMIT or glyphs(ko) <= LIMIT:
            continue
        q = rows.setdefault(jp, {"jp": jp, "ko": ko, "glyphs": glyphs(ko), "over": glyphs(ko) - LIMIT, "entries": []})
        if r["entry"] not in q["entries"]:
            q["entries"].append(r["entry"])
    out = sorted(rows.values(), key=lambda q: (q["entries"][0], q["jp"]))
    p = ROOT / "translation_memory/fit40_queue.jsonl"
    p.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in out), encoding="utf-8")
    c = collections.Counter(min(q["over"], 10) for q in out)
    print(len(out), "strings over", LIMIT, "glyphs; by excess:", dict(sorted(c.items())))
    print("with tokens:", sum(1 for q in out if TOK.search(q["jp"])))


if __name__ == "__main__":
    main()

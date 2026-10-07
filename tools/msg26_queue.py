"""Mission messages (entries >= 5500, path [0, n], 2-digit prefix) are one line of about 26 glyphs (issue #13: a literal
"\\n" is drawn as "¥n", there is no line break in this bar). Lists the Korean messages over the limit.

Counted like the bar: ESC colour codes are not glyphs, spaces are, %s (a name) counts as 4.
Uses pc_ko_A..M only (pc_ko_N is the output of the fix). Writes translation_memory/msg26_queue.jsonl.
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
ESC = re.compile(r"\x1b[A-Z][0-9A-Z]?")
LIMIT = 26


def glyphs(s):
    s = ESC.sub("", s).replace("%s", "%%%%")
    return len(s)


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_N":
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    out, seen = [], set()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if r["entry"] < 5500 or r["path"][0] != 0 or len(r["path"]) != 2 or not re.match(r"\d\d", jp) or jp in seen:
            continue
        seen.add(jp)
        ko = (ov.get(jp, r["ko"]) or "").replace("미나모토 요시츠네", "미나모토노 요시츠네").replace("양베에", "료베에")
        body = ko[2:].replace("\\n", " ")
        if glyphs(body) > LIMIT:
            out.append({"key": [r["entry"], r["path"]], "jp": jp, "ko": ko[:2] + body, "glyphs": glyphs(body)})
    q = ROOT / "translation_memory/msg26_queue.jsonl"
    q.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(len(out), "messages over", LIMIT, "->", q.name)


if __name__ == "__main__":
    main()

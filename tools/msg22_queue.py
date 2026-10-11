"""Issue #17 (2026-10-11): the live mission message (centre of the screen during battle) is cut at about 22 cells,
narrower than the 26-glyph log line used for issue #13. Measured on the reporter's 2560x1440 shot:
"시바타　카츠이에, 오다군 본진 방어를 위해 진" and "오다　노부타다의 패주에 주의하며 조비를 격" are what shows.

Width model: full-width glyph (Hangul, CJK, full-width space/punctuation) = 1 cell, ASCII (space , ! ? . %) = 0.5,
%s (an officer name, up to 8 glyphs "성　이름") = 8. ESC colour codes take no room. Limit 21 (one cell margin).

Reads the current Korean (pc_ko_* overrides on pc_match), lists mission messages (entries >= 5500, path [0, n],
2-digit prefix) over the limit. Writes translation_memory/msg22_queue.jsonl.
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
ESC = re.compile(r"\x1b[A-Z][0-9A-Z]?")
LIMIT = 21
NAME = 8


def cells(body):
    s = ESC.sub("", body).replace("%s", "\0")
    return sum(NAME if ch == "\0" else (0.5 if ord(ch) < 0x80 else 1) for ch in s)


def current(skip_from="pc_ko_R"):
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= skip_from:
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    return ov


def messages(ov):
    seen = set()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if r["entry"] < 5500 or r["path"][0] != 0 or len(r["path"]) != 2 or not re.match(r"\d\d", jp) or jp in seen:
            continue
        seen.add(jp)
        yield r["entry"], r["path"], jp, ov.get(jp, r["ko"]) or ""


def main():
    out = []
    for e, path, jp, ko in messages(current()):
        if re.match(r"\d\d", ko) and cells(ko[2:]) > LIMIT:
            out.append({"key": [e, path], "jp": jp, "ko": ko, "cells": cells(ko[2:])})
    q = ROOT / "translation_memory/msg22_queue.jsonl"
    q.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(len(out), "messages over", LIMIT, "cells ->", q.name)


if __name__ == "__main__":
    main()

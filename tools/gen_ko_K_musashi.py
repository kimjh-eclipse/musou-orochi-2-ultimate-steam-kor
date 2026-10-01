"""Odawara: keep Daji/Kaihime's 武蔵さん as 무사시 씨, including reused battle rows."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fit40_queue import glyphs
from ko_encode import can_encode, decode
from kt_text import walk
from pc_idx import Archive

TARGETS = {14996: 1, 15017: 1, 15076: 2, 15101: 1}
OLD = "무사시\x1bR 님"
PARTICLES = {"을": "를", "과": "와", "이": "가", "도": "도", "!": "!"}

matches = {}
for line in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
    row = json.loads(line)
    if row["entry"] == 34 and row["path"] in ([i] for i in TARGETS):
        matches[row["path"][0]] = row["jp"]
assert set(matches) == set(TARGETS), matches.keys()

current = {r.path[0]: decode(r.raw) for r in walk(Archive("CHS", ROOT / "build/test22").read(34), "<")}
rows = []
for idx, count in TARGETS.items():
    jp, old = matches[idx], current[idx]
    assert jp.count("武蔵\x1bRさん") == count, (idx, jp)
    assert old.count(OLD) == count, (idx, old)
    new = old
    for before, after in PARTICLES.items():
        new = new.replace(OLD + before, "무사시\x1bR 씨" + after)
    assert OLD not in new, (idx, new)
    assert re.findall(r"\x1b(?:[AC][0-9]|P.|R)", old) == re.findall(r"\x1b(?:[AC][0-9]|P.|R)", new)
    assert can_encode(new) and glyphs(new) <= 40, (idx, glyphs(new))
    rows.append({"jp": jp, "ko": new})

out = ROOT / "translation_memory/pc_ko_K_musashi.jsonl"
out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
print(f"{len(rows)} unique strings -> {out.name}")

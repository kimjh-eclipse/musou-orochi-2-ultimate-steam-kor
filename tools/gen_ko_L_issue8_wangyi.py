"""Issue #8: keep Wang Yi's casual question casual in both stage tables."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fit40_queue import glyphs
from ko_encode import can_encode, decode
from kt_text import walk
from pc_idx import Archive

TARGETS = {(34, (31073,)), (5837, (2, 9))}
OLD = "적은 아닌 것 같네.\n당신들도 요마와 싸우고 있나요?"
NEW = "적은 아닌 것 같네.\n당신들도 요마와 싸우는 거야?"

matches = {}
for line in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
    row = json.loads(line)
    key = (row["entry"], tuple(row["path"]))
    if key in TARGETS:
        matches[key] = row["jp"]
assert set(matches) == TARGETS
assert len(set(matches.values())) == 1
jp = next(iter(matches.values()))
assert jp == "敵ではなさそうね。\nあなたたちも、妖魔と戦っているのかしら"

archive = Archive("CHS", ROOT / "build/test23")
for entry in sorted({key[0] for key in TARGETS}):
    current = {row.path: decode(row.raw) for row in walk(archive.read(entry), "<")}
    for _, path in (key for key in TARGETS if key[0] == entry):
        assert current[path] == OLD, (entry, path, current[path])
assert can_encode(NEW) and glyphs(NEW) <= 40

out = ROOT / "translation_memory/pc_ko_L_issue8_wangyi.jsonl"
out.write_text(json.dumps({"jp": jp, "ko": NEW}, ensure_ascii=False) + "\n", encoding="utf-8")
print(out.name, "->", len(TARGETS), "stored rows")

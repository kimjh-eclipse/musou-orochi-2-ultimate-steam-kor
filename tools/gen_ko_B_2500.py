"""Batch B 2500-2781: numbered placeholders (tactic skill, orb, temp orb, battle art, sub scenario, request)."""
import json, re
from pathlib import Path

TM = Path(__file__).resolve().parents[1] / "translation_memory"
FW = str.maketrans("０１２３４５６７８９", "0123456789")
RULES = [(r"戦術スキル", "전술 스킬"), (r"カリホウジュ", "임시 보주"), (r"宝珠", "보주"), (r"戦技", "전기"),
         (r"サブシナリオ", "서브 시나리오"), (r"依頼", "의뢰")]
out = []
for l in (TM / "queue_B.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    n, s = r["n"], r["jp"]
    if n < 2500:
        continue
    for jp, ko in RULES:
        if m := re.fullmatch(jp + r"([0-9０-９]+)", s):
            out.append({"n": n, "ko": ko + m.group(1).translate(FW)})
            break
    else:
        raise KeyError((n, s))
with (TM / "ko_B_2500.jsonl").open("w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
print(len(out))

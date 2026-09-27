"""Batch C: placeholder / reserve strings translated by rule (numbers kept exactly as in the source)."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TM = ROOT / "translation_memory"
N = r"([０-９0-9]+)"
RULES = [
    (rf"^ＤＬＣ説明文予備{N}$", r"DLC 설명문 예비\1"), (rf"^ＤＬＣ予備{N}$", r"DLC 예비\1"),
    (rf"^予備{N}_解放$", r"예비\1_해방"), (rf"^予備{N}の説明文$", r"예비\1의 설명문"), (rf"^予備{N}$", r"예비\1"),
    (rf"^DLC用戦術{N}の説明文$", r"DLC용 전술\1의 설명문"), (rf"^説明文予備{N}$", r"설명문 예비\1"),
    (rf"^戦術スキル{N}の説明文$", r"전술 스킬\1의 설명문"), (rf"^戦技{N}の説明文$", r"전기\1의 설명문"),
    (rf"^サブシナ{N}の説明文$", r"서브 시나리오\1의 설명문"), (rf"^戦術{N}の説明文$", r"전술\1의 설명문"),
    (rf"^パーツ説明文予備{N}$", r"파츠 설명문 예비\1"), (rf"^パーツ予備{N}$", r"파츠 예비\1"),
    (rf"^コスチューム{N}$", r"코스튬\1"), (rf"^説明文・宝珠{N}$", r"설명문・보주\1"), (rf"^依頼{N}の説明文$", r"의뢰\1의 설명문"),
    (rf"^無双武将予備{N}$", r"무쌍 무장 예비\1"),
]
EXACT = {"予備": "예비", "ダミー": "더미", "戦場説明文の仮テキストです": "전장 설명문 임시 텍스트입니다",
         "デュエルモード予備": "듀얼 모드 예비", "ダミーです": "더미입니다", "ＤＬＣを購入する": "DLC 구입",
         "**ダミー**": "**더미**"}
out, miss = [], []
for l in (TM / "queue_C.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    s = r["jp"]
    ko = EXACT.get(s)
    if ko is None:
        for pat, rep in RULES:
            if re.match(pat, s):
                ko = re.sub(pat, rep, s)
                break
    if ko is None:
        miss.append(s)
        continue
    out.append({"n": r["n"], "ko": ko})
with (TM / "ko_C_rules.jsonl").open("w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
print("translated", len(out), "unmatched", len(miss), miss[:10])

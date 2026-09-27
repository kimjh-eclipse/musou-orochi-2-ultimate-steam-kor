"""6049 t0: True Musou Field editor labels, staggered lines (large + small copies). Boxes from
cc_boxes(kx=8, ky=0, core=220), read off numbered tiles; boxes holding two words are split at their gap."""
import json
from pathlib import Path
import numpy as np
from label_boxes import load
from cc_boxes import cc_boxes
from spec_6048 import split_on_gap

ROOT = Path(__file__).resolve().parents[1]
KO = {0: "전장 업로드/다운로드", 1: "전황 메시지 작성", 2: "전장 다운로드", 3: "전장 플레이", 4: "전장 업로드",
      5: "전장 업로드/다운로드", 6: "전장 신규 편집", 7: "전장 재편집", 8: "세이브", 9: "전장 확인", 10: "BGM 변경",
      11: "종료", 12: "테스트 플레이", 13: "파츠 장착", 14: "전황 메시지 작성", 15: "세이브", 16: "대사 변경",
      17: "대사 작성", 18: "대사 교체", 19: "평가 투고", 20: "무장 변경", 21: "자기 평가", 22: "평가 종료",
      23: "전장 다운로드", 24: "전장 편집", 25: "전장 업로드", 26: "전장 신규 편집", 27: "전장 플레이", 28: "추천도",
      29: "코멘트", 30: "전장 재편집", 31: ("BGM 변경", "테스트 플레이"), 32: "파츠 장착", 33: "대사 변경",
      34: "무장 변경", 35: "평가 투고", 36: "전장 확인", 37: "대사 작성", 38: "추천도", 39: ("평가 종료", "전장 편집"),
      40: ("자기 평가", "대사 교체"), 41: ("종료", "코멘트")}
d, t, im = load(6049, 0)
a = np.asarray(im.getchannel("A"))
bx = cc_boxes(a, 8, 0, core=220)
assert len(bx) == len(KO), len(bx)
labels = []
for i, b in enumerate(bx):
    ko = KO[i]
    if isinstance(ko, tuple):
        for part, k in zip(split_on_gap(a, b), ko):
            labels.append({"box": part, "ko": k, "pad": 1})
    else:
        labels.append({"box": b, "ko": ko, "pad": 1})
p = ROOT / "mapping/images/06049.json"
old = json.loads(p.read_text(encoding="utf-8"))["textures"]
p.write_text(json.dumps({"entry": 6049, "textures": [x for x in old if x["tex"] != 0] + [{"tex": 0, "labels": labels}]},
                        ensure_ascii=False), encoding="utf-8")
print(len(labels))

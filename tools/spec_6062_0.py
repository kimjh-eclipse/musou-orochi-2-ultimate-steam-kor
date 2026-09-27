"""6062 t0: gallery atlas. Menu words (large + small copies, box ids read off numbered tiles of
cc_boxes kx=10 core=200) and the character-name grid (match_names, score >= 0.9)."""
import json
from pathlib import Path
import numpy as np
from label_boxes import load
from cc_boxes import cc_boxes
from match_names import match, reference
from spec_names import NAME

ROOT = Path(__file__).resolve().parents[1]
SANS = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
MENU = ["무쌍 무장 감상", "무비 감상", "이벤트 감상", "배경화면 감상", "오로치 월드", "액션 테스트", "모델 변경", "표정 일람",
        "『무쌍 오로치』 개요", "『무쌍 오로치 마왕재림』 개요", "『무쌍 오로치 2』 개요", "촉의 장", "위의 장", "오의 장",
        "전국의 장", "오로치의 장", "대사 감상", "기록 열람", "무쌍 무장", "시나리오"]
BIG = [1, 13, 25, 48, 60, 73, 85, 97, 110, 122, 135, 147, 160, 173, 181, 182, 183, 184, 185, 186]
SMALL = [0, 12, 24, 26, 37, 49, 61, 62, 74, 86, 98, 99, 111, 123, 134, 136, 148, 161, 172, 175]
d, t, im = load(6062, 0)
a = np.asarray(im.getchannel("A"))
bx = cc_boxes(a, 10, 0, core=200)
assert len(bx) == 187, len(bx)
labels = []
for ids, right in ((BIG, 880), (SMALL, 1560)):
    for i, ko in zip(ids, MENU):
        labels.append({"box": bx[i], "ko": ko, "pad": 1, "extend_w": right - bx[i][0]})
menu = set(BIG) | set(SMALL)
rest = [i for i in range(len(bx)) if i not in menu]
res = match(a, [bx[i] for i in rest], reference())
weak = []
for i, (b, k, sc, k2, margin) in zip(rest, res):
    if sc >= 0.9:
        labels.append({"box": b, "ko": NAME[k], "first_big": True, "pad": 1})
    else:
        weak.append((i, b, NAME[k], sc, NAME[k2], margin))
# 三蔵法師 split in two boxes; 174 = "壁紙設定中" badge
u = [min(bx[149][0], bx[151][0]), min(bx[149][1], bx[151][1]), max(bx[149][2], bx[151][2]), max(bx[149][3], bx[151][3])]
labels.append({"box": u, "ko": NAME[121], "first_big": True, "pad": 1})
labels.append({"box": bx[174], "ko": "배경화면 설정 중", "font": SANS, "shear": 0, "pad": 1})
p = ROOT / "mapping/images/06062.json"
old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
p.write_text(json.dumps({"entry": 6062, "textures": [x for x in old if x["tex"] != 0] + [{"tex": 0, "labels": labels}]},
                        ensure_ascii=False), encoding="utf-8")
print(len(labels), "labels; weak", len(weak))
for w in weak:
    print("  ", w)

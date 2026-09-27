"""6061 t0: result/battle-prep atlas. Name boxes (cc_boxes kx=10 core=200) are identified by match_names
(tight glyph-core signature against the hand-read 6051 t5/t6 + 6054 atlases; accepted at score >= 0.9).
Other boxes (gear captions, result words, badges) are given by hand from the numbered tiles."""
import json
from pathlib import Path
import numpy as np
from label_boxes import load
from cc_boxes import cc_boxes
from match_names import match, reference
from spec_names import NAME

ROOT = Path(__file__).resolve().parents[1]
SANS = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
d, t, im = load(6061, 0)
a = np.asarray(im.getchannel("A"))
bx = cc_boxes(a, 10, 0, core=200)
res = match(a, bx, reference())
OTHER = {264: {"ko": "전과", "font": SANS, "shear": 0}, 285: {"ko": "보상", "font": SANS, "shear": 0},
         287: {"ko": "갱신!", "font": SANS}}
SKIP = {296, 297, 298, 286}  # gear strips / campaign badge: handled below or left
labels, weak = [], []
for i, (b, k, sc, k2, margin) in enumerate(res):
    if i in OTHER:
        labels.append({"box": b, "pad": 1, **OTHER[i]})
        continue
    if i in SKIP:
        continue
    if sc >= 0.9:
        labels.append({"box": b, "ko": NAME[k], "first_big": True, "pad": 1})
    else:
        weak.append((i, b, NAME[k], sc, NAME[k2], margin))
from spec_6048 import split_on_gap


def union(*ids):
    bs = [bx[i] for i in ids]
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]


# names that came split in two boxes / two names in one box (checked on zoomed crops)
for ids, k in (((42, 47), 121), ((128, 142), 121), ((247, 257), 54)):
    labels.append({"box": union(*ids), "ko": NAME[k], "first_big": True, "pad": 1})
for part, k in zip(split_on_gap(a, bx[267]), (130, 28)):
    labels.append({"box": part, "ko": NAME[k], "first_big": True, "pad": 1})
labels.append({"box": bx[286], "ko": "캠페인 적용 중 NEW!", "font": SANS, "pad": 1})
# gear strips: light words printed on gear icons
rgb = np.asarray(im).astype(float)
lit = (((rgb[..., :3] @ [0.299, 0.587, 0.114]) > 165) & (rgb[..., 3] > 100)).astype(np.uint8) * 255
GEARS = {297: ["방어", "적 세력", "플레이어"], 298: ["공격", "이동", "효과음", "제3세력", "최고 기록!"],
         296: ["전장", "아군 세력", "능력"]}
GEAR_BOXES = {296: [((3600, 1498, 3684, 1540), "전장"), ((3708, 1498, 3839, 1540), "아군 세력"), ((3866, 1498, 3947, 1540), "능력")],
              297: [((24, 1510, 108, 1558), "방어"), ((133, 1510, 263, 1558), "적 세력"), ((285, 1522, 372, 1566), "플레이어")],
              298: [((575, 1510, 660, 1560), "공격"), ((707, 1510, 792, 1560), "이동"), ((844, 1510, 924, 1560), "효과음"),
                    ((951, 1506, 1082, 1582), "제3세력"), ((1086, 1506, 1240, 1582), "최고 기록!")]}
for i, items in GEAR_BOXES.items():
    for w, ko in items:
        labels.append({"box": list(w), "ko": ko, "erase": "bright", "lum": 150, "ink_grow": 3, "kx": 8, "align": "center",
                       "font": SANS if ko.endswith("!") else r"C:\Windows\Fonts\NotoSerifKR-VF.ttf",
                       "style": {"grad": [[245, 245, 245]] * 8, "glow": [10, 10, 12], "glow_a": 0.6, "outline": [10, 10, 12],
                                 "has_outline": True, "fill_a": 1.0, "ink_h": int((w[3] - w[1]) * 0.8), "border": 2}})
p = ROOT / "mapping/images/06061.json"
old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
p.write_text(json.dumps({"entry": 6061, "textures": [x for x in old if x["tex"] != 0] + [{"tex": 0, "labels": labels}]},
                        ensure_ascii=False), encoding="utf-8")
print(len(bx), "boxes ->", len(labels), "labels; weak", len(weak))
for w in weak:
    print("  ", w)

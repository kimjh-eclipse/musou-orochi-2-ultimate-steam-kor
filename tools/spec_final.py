"""Last image group: battle HUD words (12913), result banners, chapter badges 14097, event title 13553,
Korean logo over the CHS logo on loading screens / wallpaper, JPN copies for thumbnail strips with English logos."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load
from spec_6048 import split_on_gap

ROOT = Path(__file__).resolve().parents[1]
SANS = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
LOGO = str(ROOT.parent / "work_wo3u/title_icon_v20260910b/logo_generated.png")
spec = {}


def add(e, entry):
    spec.setdefault(e, []).append(entry)


# HUD pickup words (CHS positions; numbers and "x2"/"600" stay)
d, t, im = load(12913, 2)
a = np.asarray(im.getchannel("A"))
b = boxes(a)
assert len(b) == 18, b
exp, _x2 = split_on_gap(a, b[13])
_600, item = split_on_gap(a, b[16])
words = {0: "체력", 1: "공격력", 2: "획득", 3: "무쌍", 4: "방어력", 5: "속도", 6: "전", 7: "회복", 8: "상승", 9: "최대",
         10: "초", 11: "귀석", 12: "무기", 17: "피버"}
labels = [{"box": b[i], "ko": ko, "font": SANS, "pad": 1, "align": "center", "grow": 1.2} for i, ko in words.items()]
labels += [{"box": exp, "ko": "경험치", "font": SANS, "pad": 1}, {"box": item, "ko": "아이템", "font": SANS, "pad": 1}]
add(12913, {"tex": 2, "labels": labels})
# result banners and level up (text boxes from boxes(); sparkles/lines around them stay)
add(12913, {"tex": 3, "labels": [{"box": [18, 313, 416, 503], "ko": "패배", "pad": 14, "align": "center", "grow": 1.1}]})
add(12913, {"tex": 4, "labels": [{"box": [1442, 18, 1844, 209], "ko": "승리", "pad": 10, "align": "center"}]})
add(12913, {"tex": 5, "labels": [{"box": boxes(np.asarray(load(12913, 5)[2].getchannel("A")))[0], "ko": "레벨 업"}]})
add(12913, {"tex": 1, "copy": "JPN"})  # English HUD art (logo, PRESS ANY KEY, K.O. COUNT, COMBO!), same layout
# chapter badges on wing ornament
d, t, im = load(14097, 1)
bx = boxes(np.asarray(im.getchannel("A")))
assert len(bx) == 10, bx
add(14097, {"tex": 1, "labels": [{"box": x, "ko": ko, "align": "center", "erase": "ink", "grow": 1.1, "shear": 0}
                                 for x, ko in zip(bx[:9], ["서장"] + [f"제{k}장" for k in range(1, 9)])]})
# event title 妖蛇討滅戦 (13553 has no PS3 offset partner)
d, t, im = load(13553, 0)
ys, xs = np.nonzero(np.asarray(im.getchannel("A")) > 12)
box = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
add(13553, {"tex": 0, "labels": [{"box": box, "ko": "요사 토벌전", "first_big": True, "pad": 0,
                                  "extend_w": min(t["w"] - box[0] - 6, int((box[2] - box[0] + 1) * 1.8))}]})
# Korean logo over the CHS logo (rects measured on 100px grids)
for e, erase in ((1077, [740, 260, 1170, 580]), (1078, [730, 180, 1190, 530]), (1079, [740, 260, 1160, 560]),
                 (31653, [1390, 715, 1770, 990])):
    add(e, {"tex": 0, "logo_over": {"src": LOGO, "rect": erase, "erase": erase, "grow": 1.08}})
for ti in (1, 13):
    add(6063, {"tex": ti, "copy": "JPN"})
# 6051 t0: faction columns (large with brush smear, dim copy); 晋 of the dim column came split in two boxes
FACTIONS = ["위", "오", "촉", "진", "기타1", "기타2", "전국1", "전국2", "전국3"]
BIG = [[21, 8, 457, 224], [20, 232, 457, 466], [24, 472, 457, 706], [43, 713, 457, 946], [34, 951, 455, 1191],
       [34, 1192, 461, 1426], [28, 1432, 501, 1676], [28, 1677, 570, 1916], [28, 1917, 564, 2159]]
DIM = [[5243, 0, 5393, 116], [5243, 117, 5390, 237], [5244, 238, 5390, 357], [5248, 361, 5388, 472],
       [5243, 477, 5463, 598], [5243, 599, 5489, 718], [5243, 719, 5489, 838], [5243, 839, 5489, 959],
       [5243, 960, 5489, 1077]]
add(6051, {"tex": 0, "labels": [{"box": b, "ko": k, "extend_w": 600 - b[0], "pad": 3, "erase": "ink"} for b, k in zip(BIG, FACTIONS)]
           + [{"box": b, "ko": k, "extend_w": 5500 - b[0], "pad": 2} for b, k in zip(DIM, FACTIONS)]})
for e, texs in spec.items():
    p = ROOT / f"mapping/images/{e:05d}.json"
    old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
    keep = [x for x in old if x["tex"] not in {y["tex"] for y in texs}]
    p.write_text(json.dumps({"entry": e, "textures": keep + texs}, ensure_ascii=False), encoding="utf-8")
print({e: [x["tex"] for x in v] for e, v in spec.items()})

"""Main menu label atlas (entry 6048): t1 selected, t5 unselected, t6 continue/new-game labels."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
MENU = ["스토리 모드", "프리 모드", "진・무쌍의 전장", "듀얼 모드", "언리미티드 모드", "갤러리", "옵션", "계속", "게임 종료"]


def split_on_gap(alpha, box):
    x0, y0, x1, y1 = box
    cols = (alpha[y0:y1 + 1, x0:x1 + 1] > 12).any(axis=0)
    best, cur, start = (0, 0), 0, 0
    for i, c in enumerate(cols):
        if not c:
            if cur == 0:
                start = i
            cur += 1
            if cur > best[0]:
                best = (cur, start)
        else:
            cur = 0
    n, s = best
    return [x0, y0, x0 + s - 1, y1], [x0 + s + n, y0, x1, y1]


spec = {"entry": 6048, "textures": []}
for ti in (1, 5):
    d, t, im = load(6048, ti)
    bx = boxes(np.asarray(im.getchannel("A")))
    assert len(bx) == 9, bx
    labels = []
    for b, ko in zip(bx, MENU):
        w = b[2] - b[0] + 1
        labels.append({"box": b, "ko": ko, "extend_w": min(t["w"] - b[0] - 2, int(w * 1.45))})
    spec["textures"].append({"tex": ti, "labels": labels})
d, t, im = load(6048, 6)
a = np.asarray(im.getchannel("A"))
bx = boxes(a)
assert len(bx) == 5, bx
left, right = split_on_gap(a, bx[2])
spec["textures"].append({"tex": 6, "labels": [
    {"box": bx[0], "ko": "이어받아 처음부터", "align": "center"},
    {"box": bx[1], "ko": "이어받아 처음부터", "align": "center"},
    {"box": left, "ko": "이어하기", "align": "center"},
    {"box": right, "ko": "처음부터", "align": "center"},
    {"box": bx[3], "ko": "이어하기", "align": "center"},
    {"box": bx[4], "ko": "처음부터", "align": "center"},
]})
# t3: chapter select titles on a wing ornament (序章, 第1章..第8章, DLC kept)
d, t, im = load(6048, 3)
bx = boxes(np.asarray(im.getchannel("A")))
assert len(bx) == 10, bx
CHAP = ["서장"] + [f"제{k}장" for k in range(1, 9)]
spec["textures"].append({"tex": 3, "labels": [
    {"box": b, "ko": ko, "align": "center", "erase": "ink", "grow": 1.1, "shear": 0} for b, ko in zip(bx[:9], CHAP)]})
out = ROOT / "mapping/images"
out.mkdir(parents=True, exist_ok=True)
(out / "06048.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
print("spec written", [len(x["labels"]) for x in spec["textures"]])

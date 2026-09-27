"""Entry 6050 t0: options menu item atlas (bold gothic italic, large column left, small column right).
Some detected boxes hold 2-3 stacked lines; they are split at the lowest-ink scanlines."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load
from image_labels import SANS

ROOT = Path(__file__).resolve().parents[1]
d, t, im = load(6050, 0)
alpha = np.asarray(im.getchannel("A"))


def split_rows(box, n):
    """Split a box holding n stacked lines: use the n runs of scanlines that contain solid ink (each grown
    to the half-way point of the gap to its neighbour); fall back to profile minima."""
    x0, y0, x1, y1 = box
    ink = (alpha[y0:y1 + 1, x0:x1 + 1] > 128).any(axis=1)
    runs, y = [], 0
    while y < len(ink):
        if ink[y]:
            s = y
            while y < len(ink) and ink[y]:
                y += 1
            runs.append([s, y - 1])
        y += 1
    runs = [r for r in runs if r[1] - r[0] >= 6]
    if len(runs) == n:
        half = min((runs[i + 1][0] - runs[i][1]) // 2 for i in range(n - 1))
        return [[x0, y0 + max(0, s - half), x1, y0 + min(len(ink) - 1, e + half)] for s, e in runs]
    prof = (alpha[y0:y1 + 1, x0:x1 + 1] > 128).sum(axis=1).astype(float)
    h = y1 - y0 + 1
    cuts = []
    for k in range(1, n):
        c = int(h * k / n)
        lo, hi = max(1, c - h // (3 * n)), min(h - 2, c + h // (3 * n))
        cuts.append(lo + int(np.argmin(prof[lo:hi + 1])))
    edges = [0] + cuts + [h - 1]
    return [[x0, y0 + edges[i] + (1 if i else 0), x1, y0 + edges[i + 1]] for i in range(n)]


KO = {"显示设定": "표시 설정", "操作设定": "조작 설정", "声音设定": "사운드 설정", "保存/载入": "세이브/로드",
      "保存": "세이브", "载入": "로드", "玩家1设定": "1P 설정", "玩家2设定": "2P 설정", "成长初始化": "성장 초기화",
      "个别武将初始化": "개별 무장 초기화", "全武将初始化": "전체 무장 초기화", "接纳异界的强者": "이계 강자 영입",
      "按键·鼠标操作设定": "키・마우스 조작 설정", "图像设定": "그래픽 설정"}
# detected boxes in order, with the Chinese label(s) each holds (read from the atlas)
LAYOUT = [
    (["显示设定", "操作设定"]), (["显示设定", "操作设定", "声音设定"]), (["声音设定"]), (["保存/载入"]),
    (["保存/载入"]), (["保存"]), (["载入"]), (["保存"]), (["玩家1设定", "玩家2设定"]), (["载入"]),
    (["成长初始化"]), (["玩家1设定", "玩家2设定"]), (["个别武将初始化", "全武将初始化"]), (["成长初始化"]),
    (["接纳异界的强者"]), (["个别武将初始化"]), (["全武将初始化"]), (["接纳异界的强者"]),
    (["按键·鼠标操作设定"]), (["图像设定"]), (["按键·鼠标操作设定"]), (["图像设定"]),
]
bx = boxes(alpha, gap=0.8)
assert len(bx) == len(LAYOUT), (len(bx), bx)
labels = []
for b, names in zip(bx, LAYOUT):
    parts = split_rows(b, len(names)) if len(names) > 1 else [b]
    for p, zh in zip(parts, names):
        right_col = p[0] > 600
        limit = (t["w"] - 4) if right_col else 630
        labels.append({"box": p, "ko": KO[zh], "font": SANS, "shear": 0.14, "extend_w": limit - p[0]})
spec = {"entry": 6050, "textures": [{"tex": 0, "labels": labels}]}

# t1: sub-screen header titles (large first character); Japanese-only captions on the same rows stay as they are
def split_on_gap(al, box):
    x0, y0, x1, y1 = box
    cols = (al[y0:y1 + 1, x0:x1 + 1] > 12).any(axis=0)
    best, cur, start = (0, 0), 0, 0
    for i, c in enumerate(cols):
        if not c:
            start = i if cur == 0 else start
            cur += 1
            if cur > best[0]:
                best = (cur, start)
        else:
            cur = 0
    n, s = best
    return [x0, y0, x0 + s - 1, y1], [x0 + s + n, y0, x1, y1]

d1, t1, im1 = load(6050, 1)
a1 = np.asarray(im1.getchannel("A"))
_, row1_cn = split_on_gap(a1, [8, 94, 911, 188])
_, row2_cn = split_on_gap(a1, [7, 190, 620, 283])
heads = [([771, 8, 901, 92], "옵션"), (row1_cn, "이계 강자 영입"), (row2_cn, "세이브/로드"), ([712, 198, 995, 283], "성장 초기화")]
spec["textures"].append({"tex": 1, "labels": [
    {"box": b, "ko": k, "first_big": True, "extend_w": t1["w"] - b[0] - 4} for b, k in heads]})
(ROOT / "mapping/images/06050.json").write_text(json.dumps(spec, ensure_ascii=False, indent=0), encoding="utf-8")
print("labels", len(labels))

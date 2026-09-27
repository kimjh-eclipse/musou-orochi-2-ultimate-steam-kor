"""Entry 6066 t0: duel-mode menu atlas. Two text columns (selected large left, unselected small right)
hold the same 26 items; portraits/flames elsewhere in the texture are untouched."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ["듀얼", "온라인", "서바이벌", "프리셋", "옵션", "메인 메뉴로", "CPU전", "대인전", "퀵 매치", "참가", "모집",
         "랭킹 표시", "무장 설정", "비기 카드 설정", "비기 카드 확인", "재대전", "듀얼 모드 메뉴로", "전투 재개",
         "재대전 희망", "표시 설정", "컨트롤러 설정", "사운드 설정", "듀얼 대전 랭킹", "서바이벌 랭킹", "초대",
         "초대장 확인"]
d, t, im = load(6066, 0)
a = np.asarray(im.getchannel("A"))
labels = []
for (x0, y0, x1, y1), limit in (((0, 0, 500, 2304), 510), ((530, 0, 930, 1630), 980)):
    m = np.zeros_like(a)
    m[y0:y1 + 1, x0:x1 + 1] = a[y0:y1 + 1, x0:x1 + 1]
    bx = [b for b in boxes(m, 0.8) if b[3] - b[1] > 30 and b[2] - b[0] > 40]
    assert len(bx) == len(ITEMS), (len(bx), bx)
    labels += [{"box": b, "ko": k, "extend_w": limit - b[0]} for b, k in zip(bx, ITEMS)]
spec = {"entry": 6066, "textures": [{"tex": 0, "labels": labels}]}

# t1: faction columns, match start/end + win banners, difficulty, "end selection", update badge.
# Boxes from region_probe.py (portraits sit right next to them, so clearing padding stays small).
FACTIONS = ["위", "오", "촉", "진", "기타1", "기타2", "전국1", "전국2", "전국3"]
BIG = [[8, 2, 184, 114], [7, 115, 184, 234], [10, 235, 184, 355], [17, 356, 184, 474], [15, 475, 216, 594],
       [15, 595, 238, 714], [12, 715, 257, 837], [12, 838, 293, 957], [12, 958, 289, 1090]]
SMALL = [[3501, 0, 3579, 57], [3500, 58, 3577, 118], [3500, 119, 3577, 178], [3503, 179, 3577, 238],
         [3490, 239, 3618, 297], [3490, 298, 3629, 358], [3501, 359, 3638, 419], [3501, 420, 3652, 479],
         [3501, 480, 3650, 539]]
t1 = [{"box": b, "ko": k, "extend_w": 330 - b[0], "pad": 3, "erase": "ink"} for b, k in zip(BIG, FACTIONS)]
t1 += [{"box": b, "ko": k, "extend_w": 3682 - b[0], "pad": 2} for b, k in zip(SMALL, FACTIONS)]
# JP order: slot 986 = 試合, slot 1906 = 開始 (shown together as "試合 開始"); CHS swapped the words
t1 += [{"box": b, "ko": k, "pad": 4, "align": "center", "grow": g} for b, k, g in (
    ([350, 40, 935, 196], "시합 개시", 1.0), ([986, 40, 1286, 196], "시합", 1.0), ([1906, 40, 2206, 196], "개시", 1.0),
    ([2283, 42, 2846, 194], "1P 승리", 1.0), ([2899, 42, 3479, 194], "2P 승리", 1.0), ([340, 276, 928, 433], "시합 종료", 1.0))]
DIFF = ["쉬움", "보통", "어려움", "수라"]
big = [[614, 1643, 740, 1714], [810, 1643, 945, 1715], [1012, 1643, 1145, 1714], [1209, 1643, 1340, 1715]]
small = [[634, 1741, 719, 1784], [834, 1741, 920, 1784], [1037, 1741, 1120, 1784], [1234, 1741, 1318, 1784]]
for row in (big, small):
    for k, (b, ko) in enumerate(zip(row, DIFF)):
        nxt = row[k + 1][0] if k + 1 < len(row) else (1368 if row is big else 1360)
        t1.append({"box": b, "ko": ko, "pad": 2, "extend_w": nxt - b[0] - 8})
t1.append({"box": [1370, 1643, 1628, 1718], "ko": "선택 종료", "pad": 2, "extend_w": 1638 - 1370})
t1.append({"box": [577, 1553, 669, 1593], "ko": "갱신!", "pad": 0, "font": r"C:\Windows\Fonts\NotoSansKR-VF.ttf"})
spec["textures"].append({"tex": 1, "labels": t1})
(ROOT / "mapping/images/06066.json").write_text(json.dumps(spec, ensure_ascii=False, indent=0), encoding="utf-8")
print("labels", len(labels))

"""Small UI label textures in entries 200 / 6049 / 6061 / 6062 / 6069 / 6071 / 6073.

Box order is label_boxes.boxes() row-major on the CHS art; texts follow the CHS positions (CHS moved some
items, e.g. 6062 t1 row 2). Terms follow the PS3 v27 translation. Textures whose JPN art is already
language-neutral (Clear! / New! / EMPTY) are copied from the JPN slot.
"""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
SANS = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
SERIF_KR = r"C:\Windows\Fonts\NotoSerifKR-VF.ttf"
EASY = ["쉬움", "보통", "어려움", "수라"]
TAGS = ["공격 증가", "방어 증가", "속도 증가", "체력 증가",
        "무쌍 증가", "배수", "견뢰", "전능력 증가",
        "진형기 강화", "연계 강화", "진형기 연장", "진형기 회복",
        "피격 회복", "백격 회복", "단독전 강화", "단독전 연장",
        "전원전 강화", "전원전 연장", "일반 내성", "이계 내성",
        "공격병 내성", "방어병 내성", "인병 내성", "원거리병 내성",
        "마법병 내성", "일반 파격", "이계 파격", "공격병 파격",
        "방어병 파격", "인병 파격", "원거리병 파격", "마법병 파격",
        "독기 증가 억제", "독기 증가 촉진", "용혈 강화", "용혈 연장",
        "부활 단축", "붕괴 경감", "진형 수렴", "전술 연마"]
TAG_STYLE = {"grad": [[250, 252, 252]] * 4 + [[225, 238, 240]] * 4, "glow": [10, 40, 48], "glow_a": 0.7,
             "outline": [12, 34, 40], "has_outline": True, "fill_a": 1.0, "ink_h": 26, "border": 2}
JOBS = {  # (entry, tex): (gap, texts, per-label options)
    (6061, 1): (0.25, ["진・무쌍의 전장 파츠 획득", "미션 결과 확인", "장비 아이템 획득", "비기 카드 획득", "전투 결과",
                      "획득 소재 일람", "획득 인연 일람", "우호도 갱신", "동료 가입", "무기 획득", "추첨"], {"first_big": True}),
    (6062, 1): (0.25, ["오로치 월드", "액션 테스트", "무쌍 무장 감상", "모델 변경", "무비 감상", "이벤트 감상", "기록 열람",
                      "배경화면 감상", "갤러리", "표정 일람", "대사 감상"], {"first_big": True}),
    (6062, 2): (0.6, ["『무쌍 오로치』 개요", "무쌍 무장", "『무쌍 오로치 마왕재림』 개요", "시나리오", "『무쌍 오로치 2』 개요"], {}),
    (6071, 76): (0.6, ["쉬움", "보통", "쉬움", "보통", "어려움", "수라", "어려움", "수라"], {"align": "center", "grow": 1.25}),
    (6049, 6): (0.6, ["쉬움", "쉬움", "보통", "보통", "어려움", "어려움"], {"align": "center", "grow": 1.25}),
    (6049, 7): (0.6, ["수라", "수라"], {"align": "center", "grow": 1.25}),
    (6069, 58): (0.6, ["등장 무쌍 무장"], {"font": SANS, "shear": 0}),
    (6069, 59): (0.6, ["미션1", "미션2", "미션3"], {"font": SANS, "shear": 0}),
    (6069, 60): (0.6, ["등장 병과"], {"font": SANS, "shear": 0}),
    (6069, 74): (0.6, ["독기 Lv."], {"font": SANS, "shear": 0}),
    (6071, 73): (0.6, ["설정 멤버"], {"font": SANS, "shear": 0}),
    (6071, 74): (0.6, ["추천 출격 멤버"], {"font": SANS, "shear": 0}),
    (6071, 75): (0.6, ["난이도 선택"], {"font": SANS, "shear": 0}),
    (6071, 40): (0.6, [f"{k}장" for k in range(1, 9)], {"align": "center", "erase": "ink", "shear": 0, "grow": 1.1}),
}
COPY_JPN = [(6071, 58), (6071, 77), (6071, 78), (6073, 9), (6073, 12), (6073, 14), (6073, 16)]
TYPES = {65: "파워", 66: "스피드", 67: "테크닉", 68: "원더"}

spec = {}
for (e, ti), (gap, texts, opt) in JOBS.items():
    d, t, im = load(e, ti)
    bx = boxes(np.asarray(im.getchannel("A")), gap=gap)
    if (e, ti) == (6071, 40):
        bx = bx[:8]  # DLC stays
    assert len(bx) == len(texts), (e, ti, len(bx), len(texts), bx)
    labels = []
    for b, ko in zip(bx, texts):
        nxt = [c for c in bx if abs(c[1] - b[1]) < 12 and c[0] > b[2]]
        right = min(c[0] for c in nxt) - 6 if nxt else t["w"] - 4
        lab = {"box": b, "ko": ko, "extend_w": right - b[0], **opt}
        if opt.get("align") == "center":
            lab.pop("extend_w")
        labels.append(lab)
    spec.setdefault(e, []).append({"tex": ti, "labels": labels})
# tactic-skill tags: 10 rows of 4 touching buttons, text drawn on the button face
for ti in (53, 54, 55):
    d, t, im = load(6069, ti)
    rows = boxes(np.asarray(im.getchannel("A")))
    assert len(rows) == 10, rows
    labels = []
    for r, (x0, y0, x1, y1) in enumerate(rows):
        cw = (x1 - x0 + 1) / 4
        for c in range(4):
            bx0, bx1 = int(x0 + c * cw), int(x0 + (c + 1) * cw) - 1
            inset = int(cw * 0.14)
            labels.append({"box": [bx0 + inset, y0 + 3, bx1 - inset, y1 - 3], "ko": TAGS[r * 4 + c], "erase": "rowfill",
                           "lum": 175, "style": TAG_STYLE, "align": "center", "font": SANS, "shear": 0})
    spec.setdefault(6069, []).append({"tex": ti, "labels": labels})
# type badges: icon + dark panel stay, only the word right of the icon is redrawn
rows = [json.loads(l) for l in (ROOT / "extract/image_textures.jsonl").open(encoding="utf-8")]
chg = {(r["entry"], r["tex"]): r.get("bbox") for r in rows}
for ti, ko in TYPES.items():
    x0, y0, x1, y1 = chg[(6069, ti)]
    spec.setdefault(6069, []).append({"tex": ti, "labels": [
        {"box": [x0 - 2, y0 - 2, x1 + 2, y1 + 2], "ko": ko, "erase": "bright", "lum": 95, "ink_grow": 2, "kx": 30,
         "font": SANS, "shear": 0, "extend_w": 250 - x0}]})
# intro card (opaque black, three centred lines found by luminance)
INTRO = ["그리고——", "수많은 영걸들이 쓰러져 갔다", "희미한 희망의 빛을 남기고……"]
d, t, im = load(6047, 0)
lum = np.asarray(im.convert("L")).astype(int)
rows_on = np.nonzero((lum > 60).sum(1) > 2)[0]
runs, s = [], None
for r in rows_on:
    if s is None:
        s = p = r
    elif r - p <= 6:
        p = r
    else:
        runs.append((s, p))
        s = p = r
runs.append((s, p))
assert len(runs) == 3, runs
WHITE = {"grad": [[250, 250, 250]] * 8, "glow": [0, 0, 0], "glow_a": 0.0, "outline": [0, 0, 0], "has_outline": False,
         "fill_a": 1.0, "ink_h": 50, "border": 2}
labels = []
for (r0, r1), ko in zip(runs, INTRO):
    cols = np.nonzero((lum[r0:r1 + 1] > 60).any(0))[0]
    labels.append({"box": [300, int(r0) - 4, 1620, int(r1) + 4], "ko": ko, "erase": "solid", "bg": [0, 0, 0, 255],
                   "align": "center", "font": SERIF_KR, "shear": 0, "style": dict(WHITE, ink_h=int(r1 - r0 + 1))})
spec.setdefault(6047, []).append({"tex": 0, "labels": labels})
# colour editor labels (6070 t0); grid/swatches around them stay
spec.setdefault(6070, []).append({"tex": 0, "labels": [
    {"box": [203, 2, 410, 38], "ko": "에디트 컬러", "pad": 1, "font": SANS, "shear": 0},
    {"box": [203, 45, 412, 82], "ko": "기본 컬러", "pad": 1, "font": SANS, "shear": 0},
    {"box": [433, 45, 466, 83], "ko": "암", "pad": 0, "font": SANS, "shear": 0, "align": "center"},
    {"box": [468, 45, 504, 83], "ko": "명", "pad": 1, "font": SANS, "shear": 0, "align": "center"}]})
for e, ti in COPY_JPN:
    spec.setdefault(e, []).append({"tex": ti, "copy": "JPN"})
for e, texs in spec.items():
    p = ROOT / f"mapping/images/{e:05d}.json"
    old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
    keep = [x for x in old if x["tex"] not in {y["tex"] for y in texs}]
    p.write_text(json.dumps({"entry": e, "textures": keep + texs}, ensure_ascii=False), encoding="utf-8")
print({e: [(x["tex"], len(x.get("labels", []))) for x in v] for e, v in spec.items()})

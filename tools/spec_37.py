"""Entry 37 leftovers: gear captions, weapon-attribute tags (text list entry 33 sec 5 from 11081), item-skill
tags, tilted stamps, difficulty buttons, small chapter badges, and language-neutral JPN art copies."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load

ROOT = Path(__file__).resolve().parents[1]
SANS = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
T = {r["path"][1]: r["ko"] for r in rows if r["entry"] == 33 and r["path"][0] == 5 and r.get("ko")}
ATTR = [T[11081 + i] for i in range(58)]
assert ATTR[0] == "염" and ATTR[31] == "천활" and ATTR[32] == "염뢰", ATTR[:3]
SKILL = ["체력 증가", "무쌍 증가", "공격 증가", "방어 증가", "속도 증가", "파워형 강화", "스피드형 강화", "테크닉형 강화",
         "원더형 강화", "무장 공격 증가", "연속 공격 증가", "교대 공격 증가", "무쌍 경감", "무장 방어 증가", "피격 경감",
         "경험치 증가", "숙련도 증가", "숙달도 증가", "귀석 증가", "운 증가", "대기 체력", "대기 무쌍", "백격 체력",
         "백격 무쌍", "백격 합력", "임사 부활"]


def st(fill, outline=(18, 10, 14), h=30):
    return {"grad": [list(fill)] * 8, "glow": list(outline), "glow_a": 0.5, "outline": list(outline),
            "has_outline": True, "fill_a": 1.0, "ink_h": h, "border": 2}


PINK, CYAN, WHITE = st((252, 236, 236)), st((226, 250, 250), (8, 26, 30)), st((250, 250, 250))
spec = {}
CHG = {(r["entry"], r["tex"]): r.get("bbox") for r in map(json.loads, (ROOT / "extract/image_textures.jsonl").open(encoding="utf-8"))}


def add(e, ti, labels):
    spec.setdefault(e, []).append({"tex": ti, "labels": labels})


def bx(e, ti, gap=0.6):
    d, t, im = load(e, ti)
    return boxes(np.asarray(im.getchannel("A")), gap=gap)


# gear captions: words sit on the gear art -> erase the light glyphs only
for ti, ko in {265: "공격", 266: "방어", 267: "이동", 268: "전장", 269: "아군 세력", 270: "적 세력", 271: "제3세력",
               272: "SE", 273: "능력", 274: "플레이어"}.items():
    b = bx(37, ti)[0]
    add(37, ti, [{"box": b, "ko": ko, "erase": "bright", "lum": 150, "ink_grow": 3, "kx": 8, "align": "center",
                  "style": st((245, 245, 245), (10, 10, 12), int((b[3] - b[1]) * 0.45))}])
# weapon-attribute tags (single / combined lists) and item-skill tags
for ti, names in ((276, ATTR[:32]), (277, ATTR[32:])):
    b = bx(37, ti)
    assert len(b) == len(names), (ti, len(b))
    add(37, ti, [{"box": [x0 + 12, y0 + 6, x1 - 12, y1 - 6], "ko": ko, "erase": "rowfill", "lum": 175, "ink_grow": 2,
                  "kx": 10, "align": "center", "font": SANS, "shear": 0, "style": PINK if (ti == 276 or i < 13) else CYAN}
                 for i, (b0, ko) in enumerate(zip(b, names)) for (x0, y0, x1, y1) in [b0]])
b = bx(37, 278)
assert len(b) == len(SKILL)
add(37, 278, [{"box": [x0 + 14, y0 + 5, x1 - 14, y1 - 5], "ko": ko, "erase": "rowfill", "lum": 175, "ink_grow": 2,
               "kx": 10, "align": "center", "font": SANS, "shear": 0, "style": st((252, 236, 236), h=24)}
              for (x0, y0, x1, y1), ko in zip(b, SKILL)])
# tilted stamps
add(37, 264, [{"box": b0, "ko": ko, "angle": 30, "pad": 2, "line_h": 34, "len_frac": 1.05} for b0, ko in zip(bx(37, 264), ["장착 완료", "장착 불가"])])
add(37, 439, [{"box": b0, "ko": ko, "angle": 30, "pad": 2, "line_h": 36, "len_frac": 1.05} for b0, ko in zip(bx(37, 439), ["수락 완료", "달성!!", "실패"])])
# panels / buttons
add(37, 317, [{"box": bx(37, 317)[0], "ko": "리더", "erase": "rowfill", "lum": 150, "kx": 30, "align": "center",
               "font": SANS, "shear": 0.1, "style": st((150, 220, 235), (5, 10, 14), 32)}])
add(37, 321, [{"box": bx(37, 321)[0], "ko": "갑", "align": "center", "font": SANS, "shear": 0}])
for ti in (380, 382):
    b = bx(37, ti)[0]
    d, tt, im = load(37, ti)
    ar = np.asarray(im).astype(float)
    lit = ((ar[..., :3] @ [0.299, 0.587, 0.114]) > 150) & (ar[..., 3] > 100)
    xs = np.nonzero(lit[b[1]:b[3] - 6].any(0))[0]
    c = [int(xs.min()), 0, int(xs.max()), 0]
    add(37, ti, [{"box": [c[0] - 2, b[1], c[2] + 9, b[3] - 9], "ko": "숙련도", "pad": 0,
                  "lum": 150, "kx": 20, "style": st((245, 245, 245), (10, 10, 12), 26)}])
add(37, 438, [{"box": [x0 + 5, y0 + 4, x1 - 5, y1 - 4], "ko": ko, "erase": "rowfill", "lum": 150, "kx": 20, "align": "center",
               "font": SANS, "shear": 0, "style": st((250, 250, 250), (10, 12, 10), 28)}
              for (x0, y0, x1, y1), ko in zip(bx(37, 438), ["쉬움", "보통", "어려움"])])
# small chapter badges (JPN: "1章"), revision mark
for ti in range(16):
    add(6071, ti, [{"box": bx(6071, ti)[0], "ko": f"{ti % 8 + 1}장", "shear": 0, "align": "center"}])
add(6071, 67, [{"box": bx(6071, 67)[0], "ko": "개", "align": "center", "shear": 0}])
# language-neutral JPN art
for ti in (314, 369, 370, 371, 372, 390, 400, 401, 402, 403, 440, 441, 457):
    spec.setdefault(37, []).append({"tex": ti, "copy": "JPN"})
spec.setdefault(200, []).append({"tex": 26, "copy": "JPN", "src": [37, 457]})
for e, texs in spec.items():
    p = ROOT / f"mapping/images/{e:05d}.json"
    old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
    keep = [x for x in old if x["tex"] not in {y["tex"] for y in texs}]
    p.write_text(json.dumps({"entry": e, "textures": keep + texs}, ensure_ascii=False), encoding="utf-8")
print({e: len(v) for e, v in spec.items()})

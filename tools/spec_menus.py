"""Shop / camp / field-editor menu atlases (6049 t8, 6055 t0 t1 t6-t10). CHS moved items against JPN, so the
texts follow the CHS art at each position. Boxes holding two touching words are split at their widest
column gap (split_on_gap from spec_6048). Terms follow PS3 v27 (판매, 연금, 연성, 식당, 진지, 추첨)."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load
from spec_6048 import split_on_gap

ROOT = Path(__file__).resolve().parents[1]
LIST = ["무기 구입", "무기 연성", "「진・무쌍의 전장」 알림", "다운로드 콘텐츠", "프로덕트 코드", "이용 코드", "추첨",
        "온라인 플레이", "소재 연금", "판매", "무기 연금", "보주 연금", "아이템 연금", "무기 판매", "보주 판매", "소재 판매",
        "의뢰", "무장 소환"]
JOBS = {  # (entry, tex): (gap, indexes of boxes to split, texts, options, keep first n boxes)
    (6049, 8): (0.18, [6], ["전장 다운로드", "전장 업로드", "코멘트", "진・무쌍의 전장", "코멘트 확인", "희소석 획득",
                           "BGM 변경", "파츠 장착", "온라인", "만족도", "무장 변경", "전장 편집", "추천도", "전장 확인",
                           "자기 평가", "평가"], {"first_big": True}, None),
    (6055, 0): (0.6, [], LIST, {}, None),
    (6055, 1): (0.6, [], LIST, {}, 18),
    (6055, 7): (0.25, [], ["프리 모드", "무기점", "추첨", "식당", "진지", "선녀"], {"first_big": True}, None),
    (6055, 8): (0.25, [], ["아이템 연금", "무기 판매", "무기 연금", "의뢰", "무장 소환", "보주 판매", "보주 연금", "판매",
                           "소재 판매", "소재 연금"], {}, None),
    (6055, 9): (0.12, [2, 3, 4], ["아이템 연금", "무장 소환", "무기 연금", "무기 판매", "보주 판매", "보주 연금",
                                  "소재 판매", "소재 연금", "의뢰", "판매"], {}, None),
    (6055, 10): (0.12, [8], ["초대 무장 선택", "무기 판매", "아이템 연금", "보주 판매", "무기 구입", "무기 연성",
                             "연회 선택", "연회 결과", "무기 연금", "보주 연금", "추첨", "판매"], {}, None),
    (6055, 6): (0.6, [], ["속성 부가"], {"font": r"C:\Windows\Fonts\NotoSansKR-VF.ttf", "shear": 0}, 1),
}
spec = {}
for (e, ti), (gap, splits, texts, opt, keep) in JOBS.items():
    d, t, im = load(e, ti)
    a = np.asarray(im.getchannel("A"))
    raw = boxes(a, gap=gap)
    if keep:
        raw = raw[:keep]
    bx = []
    for i, b in enumerate(raw):
        bx += list(split_on_gap(a, b)) if i in splits else [b]
    assert len(bx) == len(texts), (e, ti, len(bx), len(texts), bx)
    labels = []
    for b, ko in zip(bx, texts):
        nxt = [c for c in bx if abs(c[1] - b[1]) < 12 and c[0] > b[2]]
        right = min(c[0] for c in nxt) - 6 if nxt else t["w"] - 4
        labels.append({"box": b, "ko": ko, "extend_w": right - b[0], **opt})
    spec.setdefault(e, []).append({"tex": ti, "labels": labels})
for e, texs in spec.items():
    p = ROOT / f"mapping/images/{e:05d}.json"
    old = json.loads(p.read_text(encoding="utf-8"))["textures"] if p.exists() else []
    keep_t = [x for x in old if x["tex"] not in {y["tex"] for y in texs}]
    p.write_text(json.dumps({"entry": e, "textures": keep_t + texs}, ensure_ascii=False), encoding="utf-8")
print({e: [(x["tex"], len(x["labels"])) for x in v] for e, v in spec.items()})

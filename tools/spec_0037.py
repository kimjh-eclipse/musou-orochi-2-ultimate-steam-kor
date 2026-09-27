"""Entry 37: one texture per UI title / menu item (header titles with a large first character, menu items,
grey mode captions, shop captions). Textures with baked backgrounds (gears, banners, boxed buttons),
rotated stamps and dense micro atlases are left for a later pass."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load
from image_labels import SERIF, SANS

ROOT = Path(__file__).resolve().parents[1]
H, I, G, S = "header", "item", "grey", "sans"  # styles
T = {
    # header titles (large first character)
    49: ("무장 선택", H), 50: ("전장 선택", H), 51: ("전투 준비", H), 52: ("무기 장비", H), 53: ("아이템 장비", H),
    54: ("임무 수락", H), 55: ("군단 정보", H), 56: ("팀 정보", H), 57: ("옵션", H), 58: ("임무 수락 확인", H),
    59: ("정보 이력", H), 60: ("무장 정보", H), 61: ("우호도 목록", H), 62: ("경험치 분배", H),
    63: ("진・무쌍의 전장", H), 64: ("대사 변경", H), 65: ("무장 변경", H), 66: ("온라인", H), 67: ("오로치 세계", H),
    68: ("표시 설정", H), 69: ("조작 설정", H), 70: ("사운드 설정", H), 71: ("세이브/로드", H), 73: ("모델 변경", H),
    75: ("편집 내용 확인", H), 76: ("듀얼 모드", H), 77: ("듀얼", H), 78: ("서바이벌", H), 79: ("프리셋", H),
    80: ("정보 타임라인", H), 81: ("전황 정보 작성", H), 82: ("대사 교체", H), 83: ("대사 작성", H),
    84: ("시나리오 선택", H), 85: ("출격 준비", H), 86: ("컬러 에디트", H), 87: ("세이브", H), 88: ("진지", H),
    90: ("무기점", H), 91: ("식당", H), 92: ("조작 무장 변경", H), 93: ("전생", H), 94: ("성장 구슬 분배", H),
    95: ("비경 선택", H), 96: ("프리 모드", H), 97: ("그래픽 설정", H), 98: ("키・마우스 조작 설정", H),
    219: ("전투 결과", H), 220: ("진형 정보", H), 221: ("진형 설정", H), 222: ("모델 확인", H), 223: ("팀 정보", H),
    224: ("팀 이름 입력", H), 225: ("선녀", H), 226: ("정형문 선택", H),
    # grey mode captions (top-right corner)
    99: ("스토리 모드", G), 100: ("프리 모드", G), 101: ("에디트 모드", G), 102: ("갤러리", G), 103: ("옵션", G),
    104: ("듀얼 모드", G), 105: ("언리미티드 모드", G),
    # menu items (large = selected, small = unselected)
    106: ("전투 준비", I), 107: ("임무 수락", I), 108: ("군단 정보", I), 109: ("팀 정보", I), 110: ("옵션", I),
    111: ("2P 이탈", I), 113: ("메인 메뉴로", I), 114: ("전투 개시", I), 115: ("정보 이력", I),
    116: ("임무 수락 확인", I), 117: ("중간 저장", I), 118: ("전투 재개", I), 119: ("조작 무장 변경", I),
    120: ("무장 정보", I), 121: ("우호도 정보", I), 122: ("스톡 경험치 분배", I), 123: ("세이브", I),
    124: ("편집 내용 확인", I), 126: ("참가", I), 129: ("모집", I), 130: ("진군 개시", I),
    131: ("출격 예정 멤버 설정", I), 132: ("표시 설정", I), 133: ("조작 설정", I), 134: ("사운드 설정", I),
    136: ("진지 귀환", I), 137: ("성장 구슬 분배", I), 138: ("테스트 플레이 종료", I),
    139: ("키・마우스 조작 설정", I), 140: ("전투 준비", I), 141: ("임무 수락", I), 142: ("군단 정보", I),
    143: ("팀 정보", I), 144: ("옵션", I), 145: ("2P 이탈", I), 147: ("메인 메뉴로", I), 148: ("전투 개시", I),
    149: ("정보 이력", I), 150: ("임무 수락 확인", I), 151: ("중간 저장", I), 152: ("전투 재개", I),
    153: ("조작 무장 변경", I), 154: ("무장 정보", I), 155: ("우호도 정보", I), 156: ("스톡 경험치 분배", I),
    157: ("세이브", I), 158: ("편집 내용 확인", I), 160: ("참가", I), 163: ("모집", I), 164: ("진군 개시", I),
    165: ("출격 예정 멤버 설정", I), 166: ("표시 설정", I), 167: ("조작 설정", I), 168: ("사운드 설정", I),
    170: ("진지 귀환", I), 171: ("성장 구슬 분배", I), 172: ("테스트 플레이 종료", I),
    173: ("키・마우스 조작 설정", I), 174: ("난이도 선택", I), 175: ("장비 변경", I), 176: ("무기 구입", I),
    177: ("무기 연성", I), 178: ("편집 내용 확인", I), 179: ("변경 항목 선택", I), 180: ("교체 항목 선택", I),
    181: ("초대", I), 182: ("모집", I), 183: ("참가", I), 184: ("연회 선택", I), 185: ("초대 무장 선택", I),
    186: ("연회 결과", I), 187: ("분류 선택", I), 188: ("무장 선택", I), 189: ("전장 선택", I), 190: ("추첨", I),
    191: ("개별 무장 초기화", I), 192: ("조작 무장 선택", I), 193: ("비기 카드 선택", I), 194: ("스테이지 선택", I),
    195: ("랭킹 표시", I), 196: ("무장 설정", I), 197: ("비기 카드 설정", I), 198: ("비기 카드 확인", I),
    199: ("표시 설정", I), 200: ("컨트롤러 설정", I), 201: ("사운드 설정", I), 202: ("버튼 설정", I),
    203: ("작성 위치 선택", I), 205: ("아이템 연금", I), 206: ("판매", I), 207: ("무기 판매", I),
    208: ("무기 연금", I), 209: ("보주 판매", I), 210: ("보주 연금", I), 211: ("서바이벌 랭킹 표시", I),
    212: ("소재 판매", I), 213: ("소재 연금", I), 214: ("대전 랭킹 표시", I), 215: ("제1층", I), 216: ("제2층", I),
    217: ("제3층", I), 218: ("제4층", I), 227: ("전장 선택 화면으로", I), 228: ("전생", I), 229: ("진형 정보", I),
    230: ("진형 설정", I), 231: ("정보 타임라인", I), 234: ("팀 정보", I), 236: ("출격 준비", I),
    238: ("진형 스킬 설정", I), 239: ("진형 변경", I), 240: ("배치 변경", I), 241: ("전장 선택 화면으로", I),
    242: ("전생", I), 243: ("진형 정보", I), 244: ("진형 설정", I), 245: ("정보 타임라인", I), 248: ("팀 정보", I),
    250: ("출격 준비", I), 252: ("진형 스킬 설정", I), 253: ("진형 변경", I), 254: ("배치 변경", I),
    255: ("대사 작성", I), 256: ("전황 정보 작성", I), 257: ("대사 교체", I), 258: ("진・무쌍의 전장 메뉴로", I),
    259: ("대사 작성", I), 260: ("전황 정보 작성", I), 261: ("대사 교체", I), 262: ("진・무쌍의 전장 메뉴로", I),
    284: ("저장 중……", I), 300: ("불러오는 중……", I),
    # shop / equipment captions (upright gothic)
    322: ("아이템", S), 323: ("무기 판매", S), 324: ("보주 판매", S), 325: ("무기", S), 326: ("변경 후", S),
    327: ("변경 전", S), 328: ("필요 소재", S), 329: ("의뢰 보수", S), 330: ("아이템 연금", S), 331: ("보주 연금", S),
    332: ("진형 선택", S), 333: ("장비 아이템 1", S), 334: ("장비 아이템 2", S), 335: ("장비 아이템 3", S),
    336: ("장비 아이템 4", S), 337: ("장비 아이템 5", S), 338: ("장비 아이템 6", S), 342: ("획득 아이템", S),
    343: ("무기 구입", S), 344: ("무기 강화", S), 345: ("소지 무기", S), 347: ("출격 예정 멤버", S),
    348: ("무기 장비", S), 349: ("장비 중인 무기", S), 350: ("아이템 장비", S), 351: ("스킬 효과", S),
    352: ("무기 융합", S), 353: ("획득 무기", S), 354: ("아이템 변경", S), 355: ("무기 변경", S),
    356: ("무기 연성", S), 357: ("특수 관계 무장", S), 358: ("무기 버리기", S), 359: ("소재 판매", S),
    360: ("무기 연금", S),
}
MULTI = {  # texture: ([ko per box, top-to-bottom], style, align per box)
    204: (["『무쌍 오로치』 개요", "『무쌍 오로치 마왕재림』 개요", "『무쌍 오로치 2』 개요"], I, None),
    302: (["최고 기록", "누적 기록"], S, None),
    306: (["2P 메뉴 버튼을 누르십시오", "2P 참가"], S, ["left", "right"]),
    445: (["예", "예"], I, ["center", "center"]),
    446: (["아니오", "아니오"], I, ["center", "center"]),
}


def label(ko, style, box, tex_w, align="left"):
    l = {"box": box, "ko": ko, "align": align}
    if style == H:
        l["first_big"] = True
    if style in (G, S):
        l["font"] = SANS
        l["shear"] = 0.12 if style == G else 0.0
    if align == "left":
        l["extend_w"] = tex_w - box[0] - 2
    return l


spec = {"entry": 37, "textures": []}
problems = []
for ti, (ko, st) in sorted(T.items()):
    d, t, im = load(37, ti)
    bb = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not bb:
        problems.append((ti, "empty"))
        continue
    box = [bb[0], bb[1], bb[2] - 1, bb[3] - 1]
    spec["textures"].append({"tex": ti, "labels": [label(ko, st, box, t["w"])]})
for ti, (kos, st, aligns) in sorted(MULTI.items()):
    d, t, im = load(37, ti)
    bx = boxes(np.asarray(im.getchannel("A")), gap=2.0)
    if len(bx) != len(kos):
        problems.append((ti, f"{len(bx)} boxes for {len(kos)} labels"))
        continue
    labs = []
    for k, (b, ko) in enumerate(zip(bx, kos)):
        al = aligns[k] if aligns else "left"
        l = label(ko, st, b, t["w"], al)
        if al != "left":
            l.pop("extend_w", None)
        if ti == 446:
            l["grow"] = 3.2
        labs.append(l)
    spec["textures"].append({"tex": ti, "labels": labs})
# keep textures owned by other generators (spec_37.py: tags, gears, stamps, JPN copies); only ours are replaced
p = ROOT / "mapping/images/00037.json"
mine = {x["tex"] for x in spec["textures"]}
if p.exists():
    spec["textures"] += [x for x in json.loads(p.read_text(encoding="utf-8"))["textures"] if x["tex"] not in mine]
p.write_text(json.dumps(spec, ensure_ascii=False, indent=0), encoding="utf-8")
print("textures", len(spec["textures"]), "problems", problems)

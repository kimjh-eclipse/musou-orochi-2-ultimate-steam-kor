"""Issue #17: hand-written rows the part answers could not fit (names alone fill the 21 cells).
Notation {C1:text} = ESC C1 text ESC R. Long officer names are cut to the given name where the line needs it
(후쿠시마 마사노리 -> 마사노리). "exempt": names + %s alone exceed the bar even bare; the key words go first and
only the tail may be cut with long player names (colour codes may change order; same set kept).
writes translation_memory/msg22_parts/answer9_manual.jsonl (read last by gen_ko_R_msg22.py)
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = [
    ([5506, [0, 1]], "00{C2:주탄동자} 격파! {C1:%s}·{C1:요시츠네}·{C1:요시아키}", True),
    ([5506, [0, 2]], "00{C2:주탄동자} 격파! {C1:%s}·{C1:시게나리}·{C1:마사노리}", True),
    ([5506, [0, 3]], "00{C2:주탄동자} 격파! {C1:%s}·{C1:시게나리}·{C1:요시아키}", True),
    ([5524, [0, 47]], "11{C3:중앙 북쪽 요새}에 {C2:요모츠이쿠사}! {C1:%s} 발견", True),
    ([5544, [0, 38]], "00{C1:%s}·{C1:카즈마스} 구원! {C3:북서 요새} 제압", True),
    ([5544, [0, 39]], "00{C1:%s}·{C1:케이지} 구원! {C3:북서 요새} 제압", True),
    ([5545, [0, 14]], "00{C1:%s}·{C1:마사노리} {C2:손오공}으로 진군", False),
    ([5552, [0, 6]], "00{C1:%s}·{C1:%s}, {C1:%s}에게 진군!", True),
    ([5560, [0, 25]], "00{C3:북요새 남문}·{C3:남동요새 문}·{C3:중앙서요새 문} 개문", True),
    ([5615, [0, 46]], "00{C2:키요모리}·{C2:에리타테고로모}·{C2:엔엔라} 격파!", False),
    ([5637, [0, 15]], "00{C2:전위}·{C2:하후연}·{C2:%s} 중 하나 격파", False),
    ([5639, [0, 26]], "11{C1:요시모토}, {C4:%s}·{C4:마케누키} 발견!", False),
    ([5647, [0, 33]], "23{C2:%s}, {C4:하후패}·{C4:곽회} 조종!", False),
    ([5647, [0, 78]], "11{C1:%s}, {C4:마사노리}·{C4:여몽}과 출현!", False),
    ([5647, [0, 86]], "11{C4:%s}, {C1:마사노리}·{C1:여몽} 보고 신뢰!", False),
    ([5651, [0, 7]], "00{C4:%s}·{C4:정봉} 미모 대결 착각 난입!", False),
    ([5807, [0, 18]], "23{C4:마사노리}·{C4:미츠나리}, {C2:연합군} 가담!", False),
    ([5808, [0, 37]], "23{C4:다케다 신겐}·{C4:나오에 카네츠구}·{C4:아야고젠} 도착", False),
    ([5810, [0, 30]], "00{C2:%s}·{C2:요시히로}·{C2:황개} 격파하라!", False),
    ([5810, [0, 31]], "11{C2:%s}·{C2:황개}·{C2:요시히로} 모두 격파!", False),
    ([5824, [0, 26]], "00{C3:중앙 고지} {C2:카이카}·{C2:테아라이오니}·{C2:우시로메} 격파", True),
    ([5827, [0, 1]], "00{C2:촉・도쿠가와군}·{C4:연합군}, {C1:%s} 공격", True),
    ([5841, [0, 22]], "02{C2:가후}·{C2:타치바나 긴치요}·{C2:시마즈 요시히로} 격파", False),
    ([5845, [0, 1]], "00{C1:조순}·{C1:혼다 타다마사}·{C1:호죠 우지노리} 구출!", False),
    ([5845, [0, 59]], "00{C1:조순}·{C1:혼다 타다마사}·{C1:호죠 우지노리} 구출!", False),
]


def expand(s):
    return re.sub(r"\{(C[0-9A-Z]):([^}]*)\}", lambda m: "\x1b" + m.group(1) + m.group(2) + "\x1bR", s)


out = ROOT / "translation_memory/msg22_parts/answer9_manual.jsonl"
out.write_text("".join(json.dumps({"key": k, "ko": expand(s), "exempt": ex}, ensure_ascii=False) + "\n"
                       for k, s, ex in ROWS), encoding="utf-8")
print(len(ROWS), "->", out.name)

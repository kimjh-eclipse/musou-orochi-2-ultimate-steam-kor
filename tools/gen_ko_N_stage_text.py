"""Stage-select descriptions and in-battle mission messages that run past their boxes (issues #11, #12).

1. Stage-select description (33 [5, 7692..8148], 2 lines): the box shows about 24 glyphs per line (Japanese lines are
   at most 22 full-width). Lines are re-broken at a space so both lines are <= 24; texts longer than 2 x 24 use the
   hand-shortened Korean in MANUAL (translated from the Japanese, no MT).
2. Mission messages (entries >= 5500, path [0, n], 2-digit prefix): ONE line of about 26 glyphs. There is no line
   break in this bar - a literal "\\n" is drawn as "¥n" (v20261007 did that, issue #13). Messages over 26 glyphs use
   the shortened Korean translated from the Japanese in translation_memory/msg26_parts/answer*.jsonl
   (tools/msg26_queue.py -> msg26_check.py); any "\\n" is removed.
3. 両兵衛 = 료베에 (Takenaka Hanbei + Kuroda Kanbei), issue #12.
Applied after pc_ko_A..L; writes translation_memory/pc_ko_N_stage_text.jsonl. `--list` prints what still needs MANUAL.
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from ko_encode import can_encode

DESC_RANGE, DESC_LINE = (7692, 8148), 24
MSG_LINE = 26
MSG_SHORT = ROOT / "translation_memory/msg26_parts"
ESC = re.compile(r"\x1b[A-Z][0-9A-Z]?")
BREAK = "\\n"   # literal backslash + n, as in the Japanese messages

FIX = {  # (entry, path) of the first occurrence -> ko; every row with the same Japanese text gets it
    (34, (21529,)): "그때 \u001bC3동구\u001bR는 그분이 지켰지……\n재미있군요. 료베에가 함께 나서는 건가요?",
}
MANUAL = {  # stage description 33 [5, n] -> shortened Korean (2 lines of <= 24 glyphs), translated from the Japanese
    7694: "오다와라성을 지키는 요사 토벌군을 도와\n아군 거점의 함락을 막아라!",
    7697: "오다와라성에서 요마군의 주의를 돌리게\n나가시노에서 조종당하는 무장들을 구하라!",
    7698: "포위에 빈틈이 생긴 지금이 기회다!\n오다와라성을 해방해 미래의 희망을 이어라!",
    7702: "키요모리가 아네가와에서 사법 의식을 열었다.\n조종당한 동료를 구하고 키요모리를 쳐라!",
    7707: "달기의 과거를 따라 요사 출현 전의 세계로.\n앞을 가로막는 위군을 격파하라!",
    7712: "위군이 성도로 가는 길을 막는다. 조조의\n대군이 뒤에 닥치기 전에 단숨에 돌파하라!",
    7713: "수많은 싸움을 거쳐 영걸들은 하나가 됐다.\n힘을 합쳐 스사노오의 선계군에 도전하라!",
    7714: "야시오리와 슈텐도지의 힘을 빌려\n호로관에 다가오는 요사와 키요모리를 쳐라!",
    7720: "여덟 오로치를 쓰러뜨린 인간 앞에 선계군이\n가로막는다. 스사노오를 쳐서 힘을 보여라!",
    7721: "여덟 오로치를 쓰러뜨린 인간 앞을 막는\n스사노오. 복희 등과 함께 그를 쓰러뜨려라!",
    7723: "선계 수장 스사노오도 인정한 인간의 힘……\n그 총력을 다해 멸망의 운명에 맞서라!",
    7733: "동탁・원소가 요마군과 손잡았다. 그들의\n포위를 뚫고 고립무원의 역경을 뒤집어라!",
    7736: "고마키 나가쿠테에서 지장이 이끄는 부대가\n요마에게 고전 중이다. 서둘러 구원하라!",
    7754: "동구에서 오다와라성으로 지원군이 출발했다.\n이제 무쌍의 검사 미야모토 무사시를 구하라!",
    7755: "우두산을 돌파해 하세도에 들어간 여몽에게\n요마가 추격해 온다. 여몽의 철수를 도와라!",
    7756: "마고이치는 많은 부하와 고마키 나가쿠테에서\n끝까지 싸웠다. 정군산에서도 그들을 도와라!",
    7758: "사마사 등이 남긴 선단이 동관의 새 길이\n되었다. 최단 경로의 폭주를 저지하라!",
    7759: "광종의 전과로 장판으로의 귀환이 빨라졌다.\n이 기회에 전위를 동료로 끌어들여라!",
    7763: "강동의 요마군에 혼란이 생겼다고 한다.\n이 기회에 손오의 옛 땅을 되찾아라!",
    7764: "사태의 변화를 모른 채 밀려와 맞서는\n촉・도쿠가와 장수를 설득하고 요지를 지켜라!",
    7792: "유비, 도쿠가와 이에야스와 오다군을 도와\n동탁군과 싸우고 피난 못 한 백성을 구하라!",
    7794: "선녀들이 모이는 곳을 찾은 곽가와 마고이치.\n그들과 함께 선녀에게 사랑을 속삭여라!",
    7795: "복수와 임무 사이에서 괴로워하는 왕이.\n기분 전환 삼아 미카타가하라로 데려가라!",
    7800: "「자신을 쓰러뜨린 여성과 혼례를 올린다」는\n소문의 무장들을 쓰러뜨려 신랑을 얻어라!",
    7801: "적이 다가오는 가운데 남녀가 다툼을 벌였다.\n서둘러 중재하고 요마의 습격에 대비하라!",
    7803: "동탁은 간계로 미녀들을 불러 모았다.\n염원하던 주지육림의 연회에 흥을 더하라!",
    7806: "요시츠네와 닌자들이 요마의 소굴에 잠입했다.\n민첩하게 움직여 대군을 무찔러라!",
    7808: "싸움이 귀찮은 사마소와 싫은 모토나리.\n좌자의 인도로 싸움의 대의를 찾아내라!",
    7810: "누군가 사마사의 「소중한 물건」을 훔쳤다.\n무슨 수를 써서라도 범인을 찾아 되찾아라!",
    7813: "미즈치가 요마를 이끌고 키요모리를 배반했다.\n기세 오른 미즈치를 도와 키요모리를 쳐라!",
    7814: "삼국의 패자 진에 전국을 제패한 도쿠가와군이\n도전한다. 위신을 건 싸움에서 승리하라!",
    7816: "슈텐도지 일행이 연회를 계획했다. 성대한\n연회가 되도록 최고의 술과 안주를 모아라!",
    7817: "괴뢰술로 요마군 증강을 꾀하는 키요모리.\n합비를 급습해 적 무장들을 부하로 삼아라!",
    7818: "합비를 함락해 기세가 오른 요마군. 다음은\n번성이다. 군신 관우를 손에 넣어라!",
    7819: "요마군이 이쓰쿠시마를 포위. 소수로 버티는\n모리 모토나리와 함께 맹공을 막고 격퇴하라!",
    7822: "조조와 노부나가, 패도를 걷는 자들의 항쟁\n발발! 유비 등과 함께 다툼을 중재하라!",
    7823: "병기가 지키는 요새에 요마가 농성했다.\n힘자랑하는 무장들과 요새를 괴멸시켜라!",
    7824: "사격 솜씨를 겨루는 대회에 하후연이 참전!\n강적을 물리치고 명사수 칭호를 얻어라!",
    7825: "장각이 황건적을 늘리려 선계에서 유세한다.\n모든 적을 황천의 가르침으로 이끌어라!",
    7826: "요마의 급습을 받아 고립된 조조와 노부나가.\n불타는 혼노지에서 두 사람을 구출하라!",
    7827: "천하 최고의 속도를 겨루는 경주가 열렸다.\n모든 요새를 재빨리 돌며 준족을 뽐내라!",
    7828: "스사노오가 이계의 장수들에게 시련을 내렸다.\n세계를 맡길 만한지 그 힘을 가려내라!",
    7829: "위기에 빠진 요마들. 인연 있는 원소,\n이마가와 요시모토와 협력해 요마를 구하라!",
    7830: "오행산에서 토벌군에 포위된 손오공. 나타와\n함께 막는 무장을 쓰러뜨리고 포위를 뚫어라!",
    7831: "조조의 명으로 하후돈은 인재를 찾아 전장에\n선다. 무장들을 쓰러뜨려 위군에 영입하라!",
    7833: "요시츠네는 아우가 되려는 마사노리에게 시련을\n내렸다. 고금무쌍의 무예를 선보여라!",
    7834: "야망에 불타는 동탁이 다시 여관을 납치했다.\n두 방향에서 적지에 잠입해 여관을 구출하라!",
    7835: "양평관에 틀어박힌 키요모리를 요시츠네가\n급습한다. 악연의 겐페이 대결에서 승리하라!",
    7836: "세키가하라로 서두르는 히데타다와 관우.\n사나다군을 쓰러뜨리고 시즈가타케를 돌파하라!",
    7838: "호기심 많은 가라샤가 여행을 떠났다. 가는\n곳마다 생기는 골칫거리에서 가라샤를 지켜라!",
    7839: "백전연마의 노장들이 젊은이를 단련하려고\n시련을 냈다. 숙련된 기술에 도전해 이겨라!",
    7840: "키요모리의 침공을 우려해 강림한 좌자.\n인간계의 용장을 찾아 함께 키요모리를 쳐라!",
    7841: "대담한 차림의 여성이 거북한 요시츠네. 모인\n여성 무장들과 싸워 거북함을 극복하라!",
    7842: "호로관에 다가오는 연합군을 동탁은 만전의\n포진으로 맞선다. 방해하는 적을 분쇄하라!",
    7843: "요마군의 맹공 속에서 초선과 헤어진 여포.\n가득한 요마를 물리치고 초선을 구출하라!",
    7844: "와룡・봉추를 거느린 촉군에 료베에가 지휘하는\n도요토미군이 도전한다. 지략을 다해 이겨라!",
    7992: "수수께끼 바위에 불려 온 달기 일행. 강유\n등과 싸워 무슨 일이 일어나는지 지켜보라!",
    7993: "달기와 손잡고 촉・도쿠가와를 노리는 오다군.\n선수를 쳐 그들이 머무는 혼노지를 급습하라!",
    7996: "이경에서 동료들이 무기를 겨눠 왔다.\n그들과 맞붙어 설득할 기회를 만들어라!",
    8001: "타마모노마에를 살생석에 다시 봉인할 때다.\n요술에 현혹되지 말고 악한 자를 쓰러뜨려라!",
    8002: "시간을 거슬러 우에다성에 온 감녕 일행.\n타마모노마에를 찾아 신경을 되찾아라!",
    8004: "연주가 미야모토 무사시 등의 급습을 받았다.\n고전 중인 칸베에・가후 등을 구원하라!",
    8005: "우두산에서 타마모노마에를 봤다는 보고다.\n먼저 간 방통과 합류해 그녀를 찾아라!",
    8008: "요사한 술법에 현혹되지 말고 타마모노마에를\n붙잡아 신경을 얻은 경위를 캐물어라!",
    8009: "아득한 과거의 선계로 돌아간 복희 일행.\n응룡과 함께 마물을 섬멸하고 전선을 지켜라!",
    8011: "강대한 적 오로치의 출현에 혼란한 선계.\n나타・손오공과 오로치로 가는 길을 열어라!",
    8016: "선계장에게 쫓기는 요희 타마모노마에.\n세이메이・손오공과 함께 추격을 따돌려라!",
    8026: "키요모리와 손잡은 마사무네와 케이지.\n오로치 부활을 위해 토벌군을 섬멸하라!",
    8030: "아네가와에서 사악한 의식을 시작한 키요모리.\n의식을 막고 토벌군과 함께 키요모리를 쳐라!",
    8037: "용장을 꼭두각시로 삼으려 요마군이 온다.\n추격을 따돌리고 적벽을 돌파하라!",
    8038: "사술을 쓰는 키요모리를 정군산에 몰아넣었다.\n야망을 꺾기 위해 키요모리를 격파하라!",
    8039: "영웅들의 힘을 시험하는 모의전이 준비됐다.\n세이메이・제갈량・장각에게 도전하라!",
    8042: "아득한 과거의 선계에서 마물에게 습격당한\n선계장을 구하려 소수로 적진을 돌파하라!",
    8138: "규슈 전투를 클리어하고 소교, 긴치요,\n손상향 사이의 우호도를 높이면 개방됩니다",
    8141: "연사를 개방하고 고에몬, 히데요시 사이의\n우호도를 높여 대화하면 개방됩니다",
}


def glyphs(s):
    return len(ESC.sub("", s))


def msg_glyphs(s):
    return len(ESC.sub("", s).replace("%s", "%%%%"))


def rebreak(text, limit):
    """Join the lines and break once at the space that best balances two lines of <= limit glyphs."""
    flat = text.replace("\n", " ").replace("  ", " ").strip()
    best, colour = None, False
    for k, ch in enumerate(flat):
        if ch == "\x1b" and k + 1 < len(flat):
            colour = flat[k + 1] == "C"          # ESC C<n> ... ESC R = a coloured name; never break inside it
        if ch != " " or colour:
            continue
        a, b = flat[:k], flat[k + 1:]
        if glyphs(a) <= limit and glyphs(b) <= limit:
            score = abs(glyphs(a) - glyphs(b))
            if best is None or score < best[0]:
                best = (score, a + "\n" + b)
    return best[1] if best else None


def main():
    listing = "--list" in sys.argv
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_N_stage_text.jsonl":
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    short = {}
    for f in sorted(MSG_SHORT.glob("answer*.jsonl")):
        for l in open(f, encoding="utf-8"):
            if l.strip():
                a = json.loads(l)
                short[json.dumps(a["key"])] = a["ko"]
    out, todo, seen = {}, [], set()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if not jp or jp in seen:
            continue
        ko = ov.get(jp, r["ko"]) or ""
        e, p = r["entry"], r["path"]
        if (e, tuple(p)) in FIX:
            seen.add(jp)
            out[jp] = FIX[(e, tuple(p))]
            continue
        if e == 33 and p[0] == 5 and DESC_RANGE[0] <= p[1] <= DESC_RANGE[1] and jp.count("\n") == 1:
            seen.add(jp)
            ko = ko.replace("양병위", "료베에")
            if all(glyphs(x) <= DESC_LINE for x in ko.split("\n")) and ko.count("\n") <= 1:
                if ko != (ov.get(jp, r["ko"]) or ""):
                    out[jp] = ko
                continue
            if p[1] in MANUAL:
                out[jp] = MANUAL[p[1]]
                continue
            new = rebreak(ko, DESC_LINE)
            if new:
                out[jp] = new
            else:
                todo.append((p, jp, ko))
            continue
        if e >= 5500 and p[0] == 0 and len(p) == 2 and re.match(r"\d\d", jp):
            seen.add(jp)
            body = ko[2:].replace("미나모토 요시츠네", "미나모토노 요시츠네").replace("양베에", "료베에").replace(BREAK, " ")
            key = json.dumps([e, p])
            if key in short:
                body = short[key][2:]
            if msg_glyphs(body) > MSG_LINE:
                todo.append((p, jp, ko))
            if ko[:2] + body != ko:
                out[jp] = ko[:2] + body
    for jp, ko in out.items():
        assert can_encode(ko.replace(BREAK, "")), ko
    for jp, ko in MANUAL.items():
        lines = ko.split("\n")
        assert len(lines) == 2 and all(glyphs(x) <= DESC_LINE for x in lines), ko
    dest = ROOT / "translation_memory/pc_ko_N_stage_text.jsonl"
    dest.write_text("".join(json.dumps({"jp": j, "ko": k}, ensure_ascii=False) + "\n" for j, k in out.items()),
                    encoding="utf-8")
    print(f"{len(out)} rows -> {dest.name}; still too long: {len(todo)}")
    if listing:
        for p, jp, ko in todo:
            print(json.dumps({"path": p, "jp": jp, "ko": ko}, ensure_ascii=False))


if __name__ == "__main__":
    main()

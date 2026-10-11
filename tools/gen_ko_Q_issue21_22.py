"""Issues #21/#22 (2026-10-11), applied after pc_ko_A..P.

#21 (user decision): Daji's 〇〇さん is 〇〇 씨, not 님 (she says 様/님 only to Orochi). Rows picked by reading the
    scenes (no speaker ids in the data): Daji's lines, and the casual speakers in the same scenes. Polite speakers
    (Kaguya, Fukushima, Ma Dai ...) keep 님.
    〇〇ちゃん is written 〇〇짱 (user: "짱은 그냥 짱으로"), instead of 언니 / bare name / 야.
#22: 無影臑当 = 무영노당 (hanja reading like 양당개, 용신개; 무영 정강이받이 overflowed the equipment window).
writes translation_memory/pc_ko_Q_issue21_22.jsonl
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from fit40_queue import glyphs
from ko_encode import can_encode

SAN_ROWS = {14570, 14750, 14767, 14776, 14789, 14992, 15015, 15087, 15270, 15342, 15346, 15356, 15357, 15385,
            15849, 15878}
CHAN_NAMES = {"妲己": "달기", "卑弥呼": "히미코", "甲斐": "카이", "誾千代": "긴치요", "かぐや": "카구야",
              "尚香": "상향", "紅葉": "모미지", "元": "원", "元姫": "원희", "ホー": "포", "鮑": "포", "大喬": "대교"}
ITEMS = {"無影臑当": "무영노당", "ムエイスネアテ": "무영노당"}
# battle lines (entry 34) that went one glyph over the 40-glyph box (both lines together) after adding 짱
TRIM = {25257: ("있었네……", "있었네…"), 7611: ("진짜 삼국무쌍", "참 삼국무쌍"), 7610: ("일기당천이네!", "일기당천!"),
        7639: ("도깨비 같은 얼굴로", "도깨비 얼굴로"), 25248: ("꺾는다", "꺾어"), 7625: ("미안하데이……", "미안하데이…"),
        23518: ("후후후후.", "후후후.")}

CODE = r"\x1b(?:[AC][0-9A-Z])"
# after a vowel-final word (name or 언니) -> after 짱 / 씨
VOWEL_TO_JJANG = [(" 니가", "이"), ("니까", "이니까"), ("니가", "이"), ("이가", "이"), ("이는", "은"), ("이를", "을"), ("이랑", "이랑"), ("가", "이"),
                  ("는", "은"), ("를", "을"), ("와", "과"), ("랑", "이랑"), ("라고", "이라고"), ("로", "으로"),
                  ("야말로", "이야말로"), ("야", ""), ("아", "")]
NIM_TO_SSI = [("이야말로", "야말로"), ("이", "가"), ("은", "는"), ("을", "를"), ("과", "와"), ("으로", "로")]


def load_current():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_Q":
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    rows = {}
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if jp and jp not in rows:
            rows[jp] = (r["entry"], r["path"], ov.get(jp, r["ko"]) or "")
    return rows


def to_ssi(ko):
    def rep(m):
        rest = m.group(2)
        for a, b in NIM_TO_SSI:
            if rest.startswith(a) and not rest.startswith("이야") or (a == "이야말로" and rest.startswith(a)):
                return m.group(1) + " 씨" + b + rest[len(a):]
        return m.group(1) + " 씨" + rest
    return re.sub(r"(\x1bR) 님(.*?)(?=$|\x1b|\n)", lambda m: rep(m), ko, flags=re.S)


def to_jjang(ko, name):
    pat = re.compile(r"(" + CODE + re.escape(name) + r"\x1bR)( 언니)?([^\x1b\n]*)")

    def rep(m):
        rest = m.group(3)
        for a, b in VOWEL_TO_JJANG:
            if rest.startswith(a):
                # 아/야 only as a vocative (followed by punctuation, space or end)
                if a in ("아", "야") and rest[len(a):len(a) + 1] not in ("", " ", ",", ".", "!", "?", "…", "~"):
                    continue
                return m.group(1) + "짱" + b + rest[len(a):]
        return m.group(1) + "짱" + rest
    return pat.sub(rep, ko)


def main():
    rows = load_current()
    out, report = {}, []
    for jp, (e, path, ko) in rows.items():
        new = ko
        if e == 34 and len(path) == 1 and path[0] in SAN_ROWS:
            assert re.search(r"\x1bRさん", jp) and "님" in ko, (path, ko)
            new = to_ssi(new)
        for jn, kn in CHAN_NAMES.items():
            if re.search(CODE + re.escape(jn) + r"\x1bRちゃん", jp):
                new = to_jjang(new, kn)
        if jp in ITEMS:
            new = ITEMS[jp]
        if e == 34 and len(path) == 1 and path[0] in TRIM:
            a, b = TRIM[path[0]]
            assert a in new, (path, new)
            new = new.replace(a, b)
        if new != ko:
            out[jp] = new
            report.append((e, path, ko, new))
    bad = []
    for e, path, ko, new in report:
        if re.findall(r"\x1b[A-Z][0-9A-Z]?", ko) != re.findall(r"\x1b[A-Z][0-9A-Z]?", new):
            bad.append(("codes", path))
        if not can_encode(re.sub(r"\x1b[A-Z][0-9A-Z]?", "", new)):
            bad.append(("encode", path))
        if e == 34 and glyphs(new) > 40:   # the battle box holds 40 glyphs over both lines
            bad.append(("40", path, new))
    for b in bad:
        print("BAD", b)
    if "-v" in sys.argv:
        show = lambda s: re.sub(r"\x1b[AC].", "[", s).replace("\x1bR", "]").replace("\n", " / ")
        for e, path, ko, new in report:
            print(e, path, "|", show(ko), "=>", show(new))
    p = ROOT / "translation_memory/pc_ko_Q_issue21_22.jsonl"
    p.write_text("".join(json.dumps({"jp": k, "ko": v}, ensure_ascii=False) + "\n" for k, v in out.items()),
                 encoding="utf-8")
    print(len(out), "rows ->", p.name, "problems", len(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

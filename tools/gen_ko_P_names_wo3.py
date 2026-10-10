"""Issues #18/#19 (2026-10-10): place and person names aligned to the Warriors Orochi 3 Korean naming
(Namuwiki "무쌍 오로치 3" article, attacker-type roster: 다케다 신겐, 도요토미 히데요시, 도쿠가와 이에야스,
우에스기 겐신, 가토 키요마사 keep the established spellings; 타케나카 한베에, 쵸소카베 모토치카, 카이히메,
호죠 우지야스, 백백목귀, 주탄동자, 우귀; places 코마키 나가쿠테, 코시 성). Places not in that article follow
the aspirated form the reporter asked for (카와나카지마, 큐슈, 쿄토). つ = 츠. User decision ("무쌍 오로치 3에 맞춰").
Applied after pc_ko_A..O. Image labels (mapping/images/*.json "ko") get the same replacements (backup/*.bak_issue18).
writes translation_memory/pc_ko_P_names_wo3.jsonl
"""
import glob, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from ko_encode import can_encode

# (regex, replacement, JP substring the row must contain or None)
RULES = [
    # places
    (r"고마키", "코마키", None),
    (r"가와나카지마", "카와나카지마", None),
    (r"데도리가와", "테도리가와", None),
    (r"가네가사키", "카네가사키", None),
    (r"규슈", "큐슈", None),
    (r"교토", "쿄토", "京"),
    (r"고시(?=\s?성)", "코시", "古志"),
    (r"이쓰쿠시마", "이츠쿠시마", None),
    # persons (Sengoku)
    (r"다케나카", "타케나카", None),
    (r"켄신", "겐신", None),
    (r"호조", "호죠", "北条"),
    (r"호조", "호죠", "ホウジョウ"),
    (r"도세쓰", "도세츠", None),
    (r"초소카베", "쵸소카베", None),
    (r"가이(?=의 호랑이)", "카이", "甲斐"),
    (r"(?<=\x1bC1)가이(?=\x1bR)", "카이", "甲斐"),
    # persons (Orochi originals)
    (r"슈텐도지", "주탄동자", None),
    (r"규키", "우귀", None),
    (r"도도메키", "백백목귀", None),
    # つ = 츠
    (r"미쓰요", "미츠요", None),
    (r"하쓰하나", "하츠하나", None),
    (r"쓰바메가에시", "츠바메가에시", None),
]
RULES = [(re.compile(a), b, c) for a, b, c in RULES]
ESC = re.compile(r"\x1b[A-Z][0-9A-Z]?")


def apply(ko, jp):
    for rx, rep, need in RULES:
        if need is None or (jp is not None and need in jp):
            ko = rx.sub(rep, ko)
    return ko


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_P":
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    out, seen = {}, set()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if not jp or jp in seen:
            continue
        seen.add(jp)
        ko = ov.get(jp, r["ko"]) or ""
        new = apply(ko, jp)
        if new != ko:
            assert can_encode(ESC.sub("", new)), new
            out[jp] = new
    dest = ROOT / "translation_memory/pc_ko_P_names_wo3.jsonl"
    dest.write_text("".join(json.dumps({"jp": j, "ko": k}, ensure_ascii=False) + "\n" for j, k in out.items()), encoding="utf-8")
    print(len(out), "rows ->", dest.name)

    # image labels ("overpaint"/"labels" anywhere in the json): no JP alongside; the conditional rules are all
    # name-shaped (가토 키요마사, 고시 성, ...), so they are applied with every condition met
    n = 0
    def walk(o, name):
        hit = False
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "ko" and isinstance(v, str):
                    new = apply(v, "京古志甲斐北条")
                    if new != v:
                        assert can_encode(new.replace("\n", "")), new
                        print("  img", name, v.replace("\n", "/"), "->", new.replace("\n", "/"))
                        o[k] = new
                        hit = True
                else:
                    hit |= walk(v, name)
        elif isinstance(o, list):
            for v in o:
                hit |= walk(v, name)
        return hit
    for p in sorted((ROOT / "mapping/images").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if walk(d, p.name):
            bak = ROOT / "backup" / (p.name + ".bak_issue18")
            if not bak.exists():
                shutil.copy2(p, bak)
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            n += 1
    print(n, "image json files updated")


if __name__ == "__main__":
    main()

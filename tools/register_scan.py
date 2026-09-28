"""Heuristic scan: dialogue strings whose sentences end in different speech levels (register mixing inside one line).

Levels by the last word of each sentence: formal (습니다/ㅂ니까/십시오), polite (…요/죠), hao (…오/소/구려),
plain (다/어/아/야/지/냐/니/자/라/군/네/걸/마/게). Mixing formal/polite with plain or hao inside one string is flagged.
Heuristic only (quotes, self-talk and exclamations cause false hits): an estimate of scale, not a fix list.
usage: register_scan.py [--dump out.jsonl]
"""
import collections, glob, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
ESC = re.compile(r"\x1b(?:[AC][0-9]|P.|R)")


def level(word):
    w = re.sub(r"[^가-힣]", "", word)
    if not w:
        return None
    if re.search(r"(다니|라니|이라니|위해|대로|처럼|니까|으니|려고|도록|면서|지만|는데|은데|거늘)$", w):
        return None   # exclamation / connective fragments: no speech level
    if re.search(r"(습니다|ㅂ니다|니다|습니까|십시오|십시다|ㅂ시다|갑시다|합시다|읍시다|봅시다|시다)$", w):
        return "formal"
    if re.search(r"(요|죠)$", w):
        return "polite"
    if re.search(r"(오|소|구려|시오|리다|이다만)$", w) and not re.search(r"(보소|하소|주오)$", w) or re.search(r"(하오|겠소|했소|이오|있소|없소|구려)$", w):
        return "hao"
    if re.search(r"(다|어|아|야|지|냐|니|자|라|군|네|걸|마|게|래|해|대|냐고|거든|잖아|구나|려무나)$", w):
        return "plain"
    return None


def levels(s):
    s = ESC.sub("", s).replace("\\n", "\n")
    s = re.sub(r"「[^」]*」|『[^』]*』|\"[^\"]*\"", "", s)
    out = []
    for sent in re.split(r"[.!?…~]+|\n", s):
        words = sent.split()
        if words:
            lv = level(words[-1])
            if lv:
                out.append(lv)
    return out


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    seen, hits = set(), []
    cnt = collections.Counter()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if r["entry"] in (33, 53) or not jp or jp in seen:   # 33 = UI/help, 53 = narration
            continue
        ko = ov.get(jp, r["ko"] if r["level"] in ("exact_path", "entry_text", "global_text", "conflict", "global_fill") else None)
        if not ko:
            continue
        seen.add(jp)
        lv = set(levels(ko))
        cnt["lines"] += 1
        hon = lv & {"formal", "polite"}
        low = lv & {"plain", "hao"}
        if hon and low:
            kind = "+".join(sorted(lv))
            cnt[kind] += 1
            hits.append({"entry": r["entry"], "path": r["path"], "jp": jp, "ko": ko, "levels": sorted(lv)})
    print("unique dialogue strings", cnt.pop("lines"))
    print("mixed honorific + plain/hao:", len(hits))
    for k, v in cnt.most_common():
        print(f"  {k}: {v}")
    by_entry = collections.Counter(h["entry"] if h["entry"] in (34, 51, 52, 44, 49) else ("char" if h["entry"] <= 260 else "stage") for h in hits)
    print("by entry:", dict(by_entry))
    if "--dump" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--dump") + 1])
        out.write_text("".join(json.dumps(h, ensure_ascii=False) + "\n" for h in hits), encoding="utf-8")
        print("wrote", out)


if __name__ == "__main__":
    main()

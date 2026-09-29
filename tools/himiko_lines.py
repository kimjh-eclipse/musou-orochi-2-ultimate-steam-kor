"""Full survey of Himiko (卑弥呼) lines for the Gyeongsang dialect (issue #6 follow-up).

Sources: battle entry 172 (all); elsewhere lines in her Kansai-ben (うち + へん/ねん/や/で..., 妲己ちゃん, いてこま,
あかん ...), excluding the Kyoto speech of Okuni (どす, はる, ～え). Each Korean sentence is checked for Gyeongsang
markers; lines where no sentence carries one are listed.
writes translation_memory/himiko_queue.jsonl (all candidates with a flag) and prints the lines without dialect.
"""
import glob, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
HIMI = re.compile(r"妲己\x1bRちゃん|妲己ちゃん|いてこま|っちゅう|健気な少女|可憐な少女|いたいけな少女"
                  r"|うち[がはもの、をにとやらで].*(へん|ねん|や[！。…？]|やで|やん|で[！～]|たる|あかん|ちゃう|もん)"
                  r"|(へん|ねん|やで|やん|あかん|ちゃう|っちゅう|せえへん|しよる).*うち[がはもの、をにと]")
KYOTO = re.compile(r"どす|はる|おくれやす|ますえ|しまへん|え？$")
GS = re.compile(r"(데이|아이가|아이다|아이잖|노[!?.…~ ]|노$|하노|카노|기가|기고|기제|거제|이제[?!]|나[?]|가[?]|제[?!.…]|제$|끼다|끼가|카이|카는|캐도|캤|도[!.]|도$"
                r"|마[!.]|마$|삐[라려]|퍼뜩|억수|내는|내도|내랑|내가 |니[가도는,! ]|니$|그라믄|머꼬|와 |갑다|래이|하이소|더나|심더|꼬[!?.]|아이|된데이|간데이)")


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
    seen, out = set(), []
    for r in rows:
        jp = r["jp"] or ""
        if not jp or jp in seen:
            continue
        if r["entry"] == 172 or (HIMI.search(jp) and not KYOTO.search(jp)):
            seen.add(jp)
            ko = ov.get(jp, r["ko"]) or ""
            ok = bool(GS.search(ko.replace("\x1b", " ")))
            out.append({"key": [r["entry"], r["path"]], "jp": jp, "ko": ko, "dialect": ok})
    q = ROOT / "translation_memory/himiko_queue.jsonl"
    q.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    no = [x for x in out if not x["dialect"]]
    print(f"Himiko candidates {len(out)} (entry172 {sum(1 for x in out if x['key'][0] == 172)}); without dialect {len(no)}")
    for x in no:
        f = lambda s: s.replace("\n", "⏎").replace("\x1b", "")
        print(x["key"], "|", f(x["jp"])[:44], "|", f(x["ko"])[:56])


if __name__ == "__main__":
    main()

"""Collect every Xu Zhu (許褚) line for the dialect pass (issue #6 follow-up).

Sources: his battle entry 72 (all), and elsewhere lines with his speech markers (おいら, ～だよぉ, ～だかあ, すんげえ,
ありがとなあ, ～だども ...). Known other speakers using similar words are excluded by hand (EXCLUDE).
Writes translation_memory/xuzhu_queue.jsonl rows {key:[entry,path], jp, ko, ctx_prev, ctx_next} for review.
"""
import glob, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
MARK = re.compile(r"おいら|だよ[おぉ]|だか[あ？]|すんげ|ありがとなあ|だども|頑張るだ|ねえだ|くれただ|しただ|いるだか|だべ|腹減")
EXCLUDE_JP = re.compile(r"わし|俺|拙者|それがし|わらわ|あたし|私|僕|ボク|オラ|オイラ|ワシ|吾輩|我")


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
    by = {}
    for r in rows:
        by.setdefault(r["entry"], {})[tuple(r["path"])] = r
    out, seen = [], set()

    def add(r, why):
        jp = r["jp"]
        if not jp or jp in seen:
            return
        seen.add(jp)
        e, p = r["entry"], tuple(r["path"])
        tbl = by[e]
        prev = tbl.get(p[:-1] + (p[-1] - 1,))
        nxt = tbl.get(p[:-1] + (p[-1] + 1,))
        f = lambda x: (ov.get(x["jp"], x["ko"]) or "") if x and x["jp"] else ""
        out.append({"key": [e, list(p)], "why": why, "jp": jp, "ko": ov.get(jp, r["ko"]) or "",
                    "prev": f(prev), "next": f(nxt)})

    for p, r in sorted(by[72].items()):
        add(r, "entry72")
    for r in rows:
        j = r["jp"] or ""
        if r["entry"] == 72 or not MARK.search(j) or EXCLUDE_JP.search(j):
            continue
        add(r, "marker")
    q = ROOT / "translation_memory/xuzhu_queue.jsonl"
    q.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(len(out), "Xu Zhu candidates ->", q.name, "| entry72:", sum(1 for x in out if x["why"] == "entry72"))


if __name__ == "__main__":
    main()

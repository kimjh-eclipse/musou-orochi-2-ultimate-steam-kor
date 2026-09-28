"""Character-name spelling: follow the name list (entry 33 [5,...]) everywhere.
Found while fixing issue #4: 다다카쓰 / 쿠로다 / 미쓰히데 in a few narration lines (list: 타다카츠 / 구로다 / 미츠히데).
Applied on top of every earlier override (pc_ko_A..G). writes translation_memory/pc_ko_H_names.jsonl
"""
import glob, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = {"다다카쓰": "타다카츠", "쿠로다": "구로다", "미쓰히데": "미츠히데"}
JP_OF = {"다다카쓰": "忠勝", "쿠로다": "黒田", "미쓰히데": "光秀"}


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_H_names.jsonl":   # only the overrides applied before this one
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    rows, seen = [], set()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if jp in seen:
            continue
        ko = ov.get(jp, r["ko"])
        if not ko:
            continue
        new = ko
        for bad, good in FIX.items():
            if bad in new and JP_OF[bad] in jp:
                new = new.replace(bad, good)
        if new != ko:
            seen.add(jp)
            rows.append({"jp": jp, "ko": new})
    out = ROOT / "translation_memory/pc_ko_H_names.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(len(rows), "rows ->", out.name)


if __name__ == "__main__":
    main()

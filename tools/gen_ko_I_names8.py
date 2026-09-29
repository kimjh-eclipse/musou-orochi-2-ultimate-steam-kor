"""Officer names in the 8-glyph name frames (issue #6): target HP bar and camp dialogue label show 8 glyphs.

Korean names written "성　이름" (full-width space) with 9 glyphs are cut by one ("타키가와　카즈마").
Decision (2026-09-29): drop the space only for these 9-glyph names so they fit exactly (타키가와카즈마스);
names of 10+ glyphs keep their space (they overflow either way). Applied after pc_ko_A..H.
writes translation_memory/pc_ko_I_names8.jsonl
"""
import collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"[가-힣]+　[가-힣]+")
LIMIT = 8


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_I_names8.jsonl":
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    rows, seen, where = [], set(), collections.Counter()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if r["entry"] != 33 or r["path"][0] != 5 or not jp or jp in seen:
            continue
        ko = ov.get(jp, r["ko"])
        if ko and NAME.fullmatch(ko) and len(ko) == LIMIT + 1:
            seen.add(jp)
            rows.append({"jp": jp, "ko": ko.replace("　", "")})
            where[r["path"][1] // 1000] += 1
    out = ROOT / "translation_memory/pc_ko_I_names8.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(len(rows), "names ->", out.name, "| by index/1000:", dict(sorted(where.items())))


if __name__ == "__main__":
    main()

"""Unlimited-mode formation skills (陣形技, entry 33 [5,15341-15396]) and the 瘴気 term.

The HUD shows a formation skill name in 3 glyphs (every Japanese name is <= 3 characters); longer Korean names were
cut ("전원 신속" -> "전원"). Names keep the Sino-Korean reading of the kanji (user decision, 2026-09-28) and are fit
to 3 glyphs: 全 -> 전, 罠 -> 덫, 泉 -> 천. 瘴気 is 독기 everywhere (HUD "독기 Lv."); 18 strings had 장기.

writes translation_memory/pc_ko_F_skills.jsonl (build_text override, applied after pc_ko_A..E)
"""
import glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    "麻痺罠": "마비덫", "睡眠罠": "수면덫", "拘束罠": "구속덫", "衰弱罠": "쇠약덫",
    "全強壮": "전강장", "全忍耐": "전인내", "全神速": "전신속", "全突撃": "전돌격",
    "力泉": "역천", "守護泉": "수호천", "治癒泉": "치유천", "活力泉": "활력천",
    "全治癒": "전치유", "全活力": "전활력", "全完治": "전완치", "全復活": "전부활",
    "全鷲眼": "전취안", "瘴気封": "독기봉", "瘴気零": "독기영",
}


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if p.endswith("pc_ko_F_skills.jsonl"):
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    rows, seen = [], set()
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        jp = r["jp"] or ""
        if not jp or jp in seen:
            continue
        ko = ov.get(jp, r["ko"])
        if jp in NAMES:
            seen.add(jp)
            rows.append({"jp": jp, "ko": NAMES[jp]})
        elif "瘴気" in jp and ko and "장기" in ko:
            seen.add(jp)
            new = re.sub(r"장기(?!간)", "독기", ko)
            rows.append({"jp": jp, "ko": new})
    missing = set(NAMES) - {r["jp"] for r in rows}
    assert not missing, missing
    out = ROOT / "translation_memory/pc_ko_F_skills.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(len(rows), "rows ->", out.name)
    for r in rows:
        print(" ", r["jp"].replace("\n", "⏎")[:30], "->", r["ko"].replace("\n", "⏎")[:50])


if __name__ == "__main__":
    main()

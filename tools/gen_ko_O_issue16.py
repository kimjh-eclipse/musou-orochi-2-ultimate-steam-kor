"""Issues #16 and #15 (2026-10-09): name spellings, one awkward line, object names in the big HP bar.

- 黒田 구로다 -> 쿠로다: the patch writes Japanese names with aspirated initials (타다카츠, 카타쿠라, 키요모리); the name
  list's 구로다 was the odd one out (gen_ko_H had unified the narration to it). User decision.
- 片倉小十郎 코주로 -> 코쥬로 (the form fans use). Other ジュ stay 주. User decision.
- 34 [15050] Shimazu Yoshihiro (Odawara, ch.1): gambling metaphor rewritten from the Japanese.
Applied after pc_ko_A..N: every Korean row containing the old spellings is rewritten.
Image labels with 구로다 (mapping/images/*.json) are edited separately (same glyph count).
writes translation_memory/pc_ko_O_issue16.jsonl
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from ko_encode import can_encode

NAMES = {"구로다": "쿠로다", "코주로": "코쥬로"}
FIX = {  # (entry, path) -> ko
    # issue #15: the big HP bar of destructible objects (33 [5, 3800..3814]) walks the name in 2-byte steps; a 1-byte
    # ASCII space shifted the rest ("제어 장치" -> "제어□붥"). Person names use the 2-byte full-width space and show fine
    # in the same bar (issue #16 screenshot), so these four get "　" too (even byte count, spacing kept).
    (33, (5, 3800)): "나무　상자",
    (33, (5, 3805)): "제어　장치",
    (33, (5, 3806)): "동쪽　관문",
    (33, (5, 3812)): "낙석　함정",
    (34, (15050,)): "\x1bC2키요모리\x1bR 편에 걸어 크게 땄다만……\n패가 너무 좋아 따분하던 참이었지.",
}
ESC = re.compile(r"\x1b[A-Z][0-9A-Z]?")


def main():
    ov = {}
    for p in sorted(glob.glob(str(ROOT / "translation_memory/pc_ko_*.jsonl"))):
        if Path(p).name >= "pc_ko_O":
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
        new = FIX.get((r["entry"], tuple(r["path"])), ko)
        for a, b in NAMES.items():
            new = new.replace(a, b)
        if new != ko:
            assert can_encode(ESC.sub("", new)), new
            out[jp] = new
    dest = ROOT / "translation_memory/pc_ko_O_issue16.jsonl"
    dest.write_text("".join(json.dumps({"jp": j, "ko": k}, ensure_ascii=False) + "\n" for j, k in out.items()), encoding="utf-8")
    print(len(out), "rows ->", dest.name)


if __name__ == "__main__":
    main()

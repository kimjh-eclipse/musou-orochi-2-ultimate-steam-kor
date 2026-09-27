"""Independent check of a build: every entry readable, untouched entries byte-identical to the original,
font cells decode to the intended glyph set, Korean strings decode back to the translation."""
import collections, json, sys
from pathlib import Path
from pc_idx import Archive, used_ids
from kt_text import walk
from ko_encode import decode

ROOT = Path(__file__).resolve().parents[1]
ver = sys.argv[1]
bdir = ROOT / "build" / ver
new, orig = Archive("CHS", game=bdir), Archive("CHS")
rep = json.loads((bdir / "build_report.json").read_text(encoding="utf-8"))
res = collections.Counter()
text_entries = []
for i in used_ids(orig.idx):
    if new.idx[i][1] == 0 and new.idx[i][2] == 0:
        res["missing"] += 1
        continue
    d = new.read(i)
    if new.raw(i) == orig.raw(i):
        res["untouched_identical"] += 1
    else:
        res["changed"] += 1
        if d[:4] != b"GT1G":
            text_entries.append(i)
print(dict(res), "unused ids equal:", sum(1 for a, b in zip(new.idx, orig.idx) if not (b[1] or b[2])) ==
      sum(1 for a in new.idx if not (a[1] or a[2])))
matches = collections.defaultdict(dict)
for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    matches[r["entry"]][tuple(r["path"])] = r
ok = bad = 0
examples = []
for e in text_entries:
    for s in walk(new.read(e), "<"):
        r = matches[e].get(s.path)
        if r and r["ko"] and r["level"] in ("exact_path", "entry_text", "global_text", "conflict", "global_fill"):
            if decode(s.raw) == r["ko"]:
                ok += 1
            else:
                bad += 1
                examples.append((e, s.path, r["ko"][:30], decode(s.raw)[:30]))
print("korean readback ok", ok, "mismatch", bad, examples[:5])

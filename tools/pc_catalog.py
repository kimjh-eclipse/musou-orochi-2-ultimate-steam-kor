"""Catalog all text strings in the four PC language parts with the generic KT walker.

Output extract/pc_catalog.jsonl rows {entry, path, kind, JPN, CHS, ENG, CHT} (raw hex).
A string node is kept when the same path exists in JPN; per-language absence = "".
"""
import collections, json
from pathlib import Path
from pc_idx import Archive, LANGS, used_ids
from kt_text import walk

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "extract"
OUT.mkdir(exist_ok=True)

arcs = {l: Archive(l) for l in LANGS}
ids = used_ids(arcs["JPN"].idx)
rows, kinds, empty_entries = [], collections.Counter(), []
for i in ids:
    per = {}
    for l in LANGS:
        d = arcs[l].read(i)
        if d[:4] == b"GT1G":
            per = None
            break
        per[l] = {s.path: s for s in walk(d, "<")}
    if per is None:
        continue
    if not per["JPN"]:
        empty_entries.append(i)
        continue
    for path, s in per["JPN"].items():
        kinds[s.kind] += 1
        rows.append({"entry": i, "path": list(path), "kind": s.kind,
                     **{l: (per[l][path].raw.hex() if path in per[l] else None) for l in LANGS}})

with (OUT / "pc_catalog.jsonl").open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print("text entries", len({r['entry'] for r in rows}), "strings", len(rows), dict(kinds))
print("non-image entries without text", len(empty_entries), empty_entries[:20])
missing = collections.Counter(l for r in rows for l in LANGS if r[l] is None)
print("paths missing per language", dict(missing))
cjk = sum(1 for r in rows if any(b >= 0x80 for b in bytes.fromhex(r["JPN"])))
print("JPN strings with non-ASCII bytes", cjk)

heads = collections.Counter()
sizes = collections.defaultdict(list)
for i in empty_entries:
    d = arcs["JPN"].read(i)
    heads[d[:4].hex()] += 1
    sizes[d[:4].hex()].append((i, len(d)))
for h, c in heads.most_common():
    print("  empty head", h, c, sizes[h][:6])

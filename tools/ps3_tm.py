"""Extract the PS3 translation memory: original Japanese (jp_iso) vs final Korean (hdd0 v20260910b).

For every LINKDATA entry whose stored bytes differ, decode both, walk text nodes (big-endian),
pair by (entry, path) and turn PS3 donor CP932 characters back into Hangul with the final mapping.
Output translation_memory/ps3_tm.jsonl.
"""
import json, struct, sys, zlib, hashlib
from pathlib import Path
from kt_text import walk

W = Path(r"C:\Emul\Switch\패치유틸.xdeltaUI\work_wo3u")
sys.path.insert(0, str(W))
from linkdata_tool import read_index, read_entry  # PS3 BE codec

JP = W / "jp_iso/PS3_GAME/USRDIR"
HDD = Path(r"C:\Emul\PS3\rpcs3-v0.0.27-14986-db7f84f9_win64\dev_hdd0\disc\BLJM61084\PS3_GAME\USRDIR")
MAP = W / "jp_full_dialogue/v21/build/mapping.json"
OUT = Path(__file__).resolve().parents[1] / "translation_memory"
OUT.mkdir(exist_ok=True)

mapping = json.loads(MAP.read_text(encoding="utf-8"))
donor2ko = {m["donor"]: m["ko"] for m in mapping}


def ko_decode(raw):
    s = raw.decode("cp932", errors="replace")
    return "".join(donor2ko.get(c, c) for c in s)


ia, ib = read_index(JP / "LINKDATA.IDX"), read_index(HDD / "LINKDATA.IDX")
fa, fb = (JP / "LINKDATA.BIN").open("rb"), (HDD / "LINKDATA.BIN").open("rb")
changed = []
for ea, eb in zip(ia, ib):
    if (ea.offset, ea.unpacked_size, ea.stored_size, ea.compressed) != (eb.offset, eb.unpacked_size, eb.stored_size, eb.compressed):
        changed.append(ea.index)
        continue
    if ea.stored_size and ea.stored_size < 64 * 1024 * 1024:
        fa.seek(ea.offset); fb.seek(eb.offset)
        if fa.read(ea.stored_size) != fb.read(eb.stored_size):
            changed.append(ea.index)
print("changed entries", len(changed), flush=True)

rows, textless, structure_changed = [], [], []
for i in changed:
    a, b = read_entry(fa, ia[i]), read_entry(fb, ib[i])
    sa = {s.path: s for s in walk(a, ">")}
    sb = {s.path: s for s in walk(b, ">")}
    if not sa:
        textless.append((i, a[:4].hex()))
        continue
    if set(sa) != set(sb):
        structure_changed.append((i, len(sa), len(sb)))
    for path, s in sa.items():
        t = sb.get(path)
        if t is None:
            continue
        rows.append({"ps3_entry": i, "path": list(path), "kind": s.kind,
                     "jp_hex": s.raw.hex(), "jp": s.raw.decode("cp932", "replace"),
                     "ko_hex": t.raw.hex(), "ko": ko_decode(t.raw), "changed": s.raw != t.raw})
with (OUT / "ps3_tm.jsonl").open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
report = {"changed_entries": len(changed), "text_entries": len({r['ps3_entry'] for r in rows}),
          "strings": len(rows), "translated_strings": sum(r["changed"] for r in rows),
          "textless_changed_entries": textless, "structure_changed": structure_changed,
          "mapping_sha256": hashlib.sha256(MAP.read_bytes()).hexdigest().upper()}
(OUT / "ps3_tm_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()})
print("textless heads", textless[:30])

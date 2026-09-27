"""Match PC JPN strings to the PS3 translation memory.

Levels (best first):
  exact_path : PC entry paired with a PS3 entry (max shared JP strings), same path, identical JP bytes
  entry_text : same paired entry, identical JP bytes at a different path (unique KO within that entry)
  global_text: identical JP bytes anywhere in PS3 with a single KO rendering
  conflict   : identical JP bytes with several KO renderings (kept for review; majority chosen)
  untranslated_ps3 : matched but PS3 left it unchanged (JP == KO)
  unmatched  : JP bytes not found in the PS3 memory
Output mapping/pc_match.jsonl and mapping/pc_match_report.json.
"""
import collections, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "mapping").mkdir(exist_ok=True)
pc = [json.loads(l) for l in (ROOT / "extract/pc_catalog.jsonl").open(encoding="utf-8")]
tm = [json.loads(l) for l in (ROOT / "translation_memory/ps3_tm.jsonl").open(encoding="utf-8")]

by_entry = collections.defaultdict(dict)       # ps3 entry -> path -> row
jp_in_entry = collections.defaultdict(lambda: collections.defaultdict(set))
glob = collections.defaultdict(collections.Counter)
for r in tm:
    by_entry[r["ps3_entry"]][tuple(r["path"])] = r
    jp_in_entry[r["ps3_entry"]][r["jp_hex"]].add(r["ko"])
    glob[r["jp_hex"]][r["ko"]] += 1
jp_index = collections.defaultdict(set)  # jp_hex -> ps3 entries
for r in tm:
    jp_index[r["jp_hex"]].add(r["ps3_entry"])

# pair PC entries with PS3 entries by shared JP strings
pc_by_entry = collections.defaultdict(list)
for r in pc:
    pc_by_entry[r["entry"]].append(r)
pairing = {}
for e, rows in pc_by_entry.items():
    votes = collections.Counter()
    for r in rows:
        if len(r["JPN"]) >= 8:
            for pe in jp_index.get(r["JPN"], ()):
                votes[pe] += 1
    if votes:
        pe, n = votes.most_common(1)[0]
        pairing[e] = (pe, n, len(rows))

out, levels = [], collections.Counter()
for r in pc:
    jp = r["JPN"]
    ko = None
    level = "unmatched"
    pe = pairing.get(r["entry"], (None,))[0]
    if pe is not None:
        t = by_entry[pe].get(tuple(r["path"]))
        if t and t["jp_hex"] == jp:
            ko, level = t["ko"], "exact_path"
        elif jp in jp_in_entry[pe] and len(jp_in_entry[pe][jp]) == 1:
            ko, level = next(iter(jp_in_entry[pe][jp])), "entry_text"
    if ko is None and jp in glob:
        c = glob[jp]
        ko = c.most_common(1)[0][0]
        level = "global_text" if len(c) == 1 else "conflict"
    jp_text = bytes.fromhex(jp).decode("cp932", "replace")
    if (ko is None or ko == jp_text) and jp in glob:
        # PS3 left this copy (or never had it); use a translated rendering of the same text elsewhere
        done = collections.Counter({k: n for k, n in glob[jp].items() if k != jp_text})
        if done:
            ko, level = done.most_common(1)[0][0], "global_fill"
    if ko is not None and ko == jp_text:
        level = "untranslated_ps3" if level != "unmatched" else level
    if not jp:
        level = "empty"
    levels[level] += 1
    out.append({**{k: r[k] for k in ("entry", "path", "kind")}, "jp": bytes.fromhex(jp).decode("cp932", "replace"),
                "chs": bytes.fromhex(r["CHS"]).decode("gbk", "replace") if r["CHS"] else None,
                "ko": ko, "level": level, "ps3_entry": pe})

with (ROOT / "mapping/pc_match.jsonl").open("w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
has_cjk = lambda s: any(ord(c) > 0x7F for c in s)
un = [r for r in out if r["level"] == "unmatched" and has_cjk(r["jp"])]
un_ent = collections.Counter(r["entry"] for r in un)
rep = {"pc_strings": len(out), "levels": dict(levels), "paired_entries": len(pairing), "pc_text_entries": len(pc_by_entry),
       "unmatched_with_japanese": len(un), "unmatched_top_entries": un_ent.most_common(25),
       "unpaired_entries": sorted(set(pc_by_entry) - set(pairing))}
(ROOT / "mapping/pc_match_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in rep.items() if k != "unpaired_entries"}, ensure_ascii=False))
print("unpaired", len(rep["unpaired_entries"]), rep["unpaired_entries"][:40])
for r in un[:15]:
    print("  UN", r["entry"], r["path"], r["jp"][:50].replace("\n", "/"))

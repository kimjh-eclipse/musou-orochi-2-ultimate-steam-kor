"""Build Korean text entries for the CHS slot from the JPN templates.

Per string (JPN path):
  Korean available            -> encode(ko)
  no Korean, JP encodable     -> encode(jp)   (ASCII / kana / symbols only)
  otherwise                   -> CHS original bytes at the same path (still Chinese; queued for translation)
"""
import collections, json
from pathlib import Path
from pc_idx import Archive
from kt_text import walk
from kt_rebuild import rebuild
from ko_encode import encode, EncodeError, can_encode

ROOT = Path(__file__).resolve().parents[1]
KO_LEVELS = {"exact_path", "entry_text", "global_text", "conflict", "global_fill"}


def load_matches():
    by = collections.defaultdict(dict)
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        by[r["entry"]][tuple(r["path"])] = r
    return by


def load_overrides():
    """translation_memory/pc_ko_*.jsonl rows {jp, ko} written for strings PS3 never translated."""
    ov = {}
    for p in sorted((ROOT / "translation_memory").glob("pc_ko_*.jsonl")):
        for l in p.open(encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                ov[r["jp"]] = r["ko"]
    return ov


def build_all():
    matches = load_matches()
    overrides = load_overrides()
    jpn, chs = Archive("JPN"), Archive("CHS")
    out, stats, problems = {}, collections.Counter(), []
    queue = []
    for e, rows in sorted(matches.items()):
        tpl = jpn.read(e)
        chs_strings = {s.path: s.raw for s in walk(chs.read(e), "<")}
        repl = {}
        for s in walk(tpl, "<"):
            r = rows.get(s.path)
            jp = s.raw.decode("cp932", "replace")
            ko = None
            if r and r["level"] in KO_LEVELS and r["ko"] is not None:
                ko = r["ko"]
            if jp in overrides:
                ko = overrides[jp]
            if ko is not None:
                try:
                    repl[s.path] = encode(ko)
                    stats["korean"] += 1
                    continue
                except EncodeError as err:
                    problems.append((e, s.path, str(err), ko[:40]))
                    stats["korean_unencodable"] += 1
            if can_encode(jp):
                repl[s.path] = encode(jp)
                stats["jp_encodable"] += 1
            elif s.path in chs_strings:
                repl[s.path] = chs_strings[s.path]
                stats["chs_fallback"] += 1
                queue.append({"entry": e, "path": list(s.path), "jp": jp})
            else:
                repl[s.path] = encode("".join(c if can_encode(c) else "?" for c in jp))
                stats["jp_lossy"] += 1
                queue.append({"entry": e, "path": list(s.path), "jp": jp})
        new = rebuild(tpl, repl)
        back = {s.path: s.raw for s in walk(new, "<")}
        assert back == repl, f"readback mismatch in entry {e}"
        out[e] = new
    return out, dict(stats), problems, queue


if __name__ == "__main__":
    out, stats, problems, queue = build_all()
    print(len(out), "entries", stats)
    for p in problems[:20]:
        print("  ", p)

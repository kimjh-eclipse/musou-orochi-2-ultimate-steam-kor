"""Forced identity rebuild: replace every string with itself; the rebuilt entry must equal the original.
Then a growth test: append 'X' * 7 to every string and confirm the walker reads the new strings back."""
import collections, sys
from pc_idx import Archive, LANGS, used_ids
from kt_text import walk
from kt_rebuild import rebuild

langs = sys.argv[1:] or LANGS
for l in langs:
    a = Archive(l)
    res = collections.Counter()
    bad = []
    for i in used_ids(a.idx):
        d = a.read(i)
        if d[:4] == b"GT1G":
            continue
        ss = walk(d, "<")
        if not ss:
            continue
        repl = {s.path: s.raw for s in ss}
        try:
            out = rebuild(d, repl)
        except ValueError as e:
            bad.append((i, str(e)))
            res["error"] += 1
            continue
        if out == d:
            res["identical"] += 1
        else:
            res["differs"] += 1
            n = next((k for k, (x, y) in enumerate(zip(out, d)) if x != y), min(len(out), len(d)))
            bad.append((i, f"len {len(out)} vs {len(d)}, first diff {n:#x}"))
        # growth test
        grow = {s.path: s.raw + b"X" * 7 for s in ss}
        out2 = rebuild(d, grow)
        back = {s.path: s.raw for s in walk(out2, "<")}
        if back != grow:
            res["growth_readback_fail"] += 1
            missing = [p for p in grow if back.get(p) != grow[p]]
            bad.append((i, f"growth readback: {len(missing)} mismatches, e.g. {missing[:2]}"))
        else:
            res["growth_ok"] += 1
    print(l, dict(res))
    for b in bad[:15]:
        print("   ", b)

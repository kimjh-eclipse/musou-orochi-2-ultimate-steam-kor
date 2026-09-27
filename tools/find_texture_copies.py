"""Search the base archives (000-003) for G1T textures whose pixel data equals given reference textures.
Compares a 64 KiB fingerprint from the middle of the level-0 data, then confirms full equality."""
import hashlib, struct, sys, zlib
from pc_idx import Archive, used_ids, decompress
from g1t_pc import parse, level0_size

refs = []
for part in ("CHS", "JPN"):
    a = Archive(part)
    for e, ti in ((6048, 1), (6048, 5)):
        d = a.read(e)
        t = parse(d)["tex"][ti]
        n = level0_size(t)
        raw = d[t["data"]:t["data"] + n]
        refs.append((part, e, ti, n, hashlib.sha1(raw[n // 2:n // 2 + 65536]).hexdigest(), hashlib.sha1(raw).hexdigest()))
fp = {r[4]: r for r in refs}
sizes = {r[3] for r in refs}
print("refs", [(r[0], r[1], r[2], r[3]) for r in refs])
for part in ("000", "001", "002", "003"):
    a = Archive(part)
    n_g1t = 0
    for e in used_ids(a.idx):
        off, un, st, c = a.idx[e]
        if un < min(sizes):
            continue
        try:
            d = a.read(e)
        except Exception:
            continue
        if d[:4] != b"GT1G":
            continue
        n_g1t += 1
        try:
            g = parse(d)
        except Exception:
            continue
        for t in g["tex"]:
            n = level0_size(t)
            if n not in sizes:
                continue
            raw = d[t["data"]:t["data"] + n]
            h = hashlib.sha1(raw[n // 2:n // 2 + 65536]).hexdigest()
            if h in fp:
                r = fp[h]
                print(f"MATCH {part} entry {e} t{t['i']} == {r[0]} {r[1]} t{r[2]} full={hashlib.sha1(raw).hexdigest() == r[5]}", flush=True)
    print(part, "large G1T scanned", n_g1t, flush=True)

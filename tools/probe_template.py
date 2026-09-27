"""Compare non-string bytes of CHS vs JPN text entries: mask every string byte, then diff what remains."""
import collections
from pc_idx import Archive, used_ids
from kt_text import walk

chs, jpn = Archive("CHS"), Archive("JPN")
stats = collections.Counter()
examples = []
for i in used_ids(jpn.idx):
    a, b = jpn.read(i), chs.read(i)
    if a[:4] == b"GT1G":
        continue
    sa, sb = walk(a, "<"), walk(b, "<")
    if not sa:
        continue
    pa, pb = {s.path for s in sa}, {s.path for s in sb}
    if pa != pb:
        stats["different string paths"] += 1
        examples.append((i, "paths", len(pa), len(pb)))
        continue
    # compare the region before the first string (tables/headers) with pointers masked out
    def skeleton(d, ss):
        first = min(s.pos for s in ss)
        buf = bytearray(d[:first])
        for s in ss:
            if s.ptr + 4 <= first:
                buf[s.ptr:s.ptr + 4] = b"\0\0\0\0"
        return bytes(buf)
    ka, kb = skeleton(a, sa), skeleton(b, sb)
    if len(ka) != len(kb):
        stats["header length differs"] += 1
        examples.append((i, "hdrlen", len(ka), len(kb)))
    elif ka != kb:
        n = sum(x != y for x, y in zip(ka, kb))
        stats["header bytes differ"] += 1
        examples.append((i, "hdrbytes", n, len(ka)))
    else:
        stats["identical skeleton"] += 1
print(dict(stats))
for e in examples[:30]:
    print(" ", e)

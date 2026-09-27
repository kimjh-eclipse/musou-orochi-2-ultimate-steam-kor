"""Decompress every entry of one language part, recompress, and confirm the payload survives."""
import collections, sys, time
from pc_idx import Archive, compress, decompress, used_ids

part = sys.argv[1] if len(sys.argv) > 1 else "CHS"
a = Archive(part)
ids = used_ids(a.idx)
stats = collections.Counter()
magic = collections.Counter()
grow = 0
t = time.time()
for i in ids:
    off, un, st, c = a.idx[i]
    data = a.read(i)
    magic[data[:4]] += 1
    if c:
        ch = a.chunk_size(i)
        stats[f"chunk_{ch:#x}"] += 1
        z = compress(data, ch)
        back, _ = decompress(z, un)
        assert back == data, i
        if len(z) > st:
            grow += 1
    else:
        stats["stored"] += 1
    # slot capacity: gap to the next entry offset
print(part, len(ids), dict(stats), "recompressed larger than original:", grow, f"{time.time()-t:.1f}s")
print("top magics:", [(k.hex(), v) for k, v in magic.most_common(15)])

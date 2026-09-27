import struct
from pc_idx import Archive

a = Archive("JPN")
for i in (5502, 14418, 36160, 54, 12912):
    d = a.read(i)
    print(f"== {i} size {len(d)}")
    for o in range(0, min(len(d), 0x80), 16):
        c = d[o:o + 16]
        print(f"  {o:04X} {c.hex(' ')}")
    n = struct.unpack_from("<I", d)[0]
    if 1 <= n <= 64:
        desc = [struct.unpack_from("<II", d, 4 + 8 * k) for k in range(n)]
        print("  desc", [(hex(o), s, d[o:o + 4].hex()) for o, s in desc])
# 0d0a text entries: find one and show decoded head
from pc_idx import used_ids
for i in used_ids(a.idx):
    d = a.read(i)
    if d[:2] == b"\r\n":
        print("== text entry", i, len(d))
        print(d[:400].decode("cp932", "replace"))
        break

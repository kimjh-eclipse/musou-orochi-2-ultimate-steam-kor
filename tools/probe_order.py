from pathlib import Path

row0 = "丏丟並丼乂亂亞伶伬伈伝"
row1 = "僈僉僨僗僝僠僣僥僨僯"
for s in (row0, row1):
    print([(c, c.encode("gbk").hex(), hex(ord(c))) for c in s])

exe = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe").read_bytes()
for c in "丏丟並":
    g = c.encode("gbk")
    u = ord(c)
    for name, pat in (("gbk BE", g), ("gbk LE", g[::-1]), ("utf16le", c.encode("utf-16-le"))):
        hits = []
        s = 0
        while len(hits) < 5:
            h = exe.find(pat, s)
            if h < 0:
                break
            hits.append(hex(h))
            s = h + 1
        print(c, name, pat.hex(), hits)
# sequence search: the first three glyph codes adjacent as u16 LE / BE
for name, fn in (("u16 LE gbk", lambda c: c.encode("gbk")[::-1]), ("u16 BE gbk", lambda c: c.encode("gbk")),
                 ("utf16le", lambda c: c.encode("utf-16-le"))):
    seq = b"".join(fn(c) for c in "丏丟")
    print(name, "pair hit", hex(exe.find(seq)))
    for stride in (4, 8, 12, 16):
        # codes spaced by stride
        a, b = fn("丏"), fn("丟")
        i = exe.find(a)
        found = None
        while i >= 0:
            if exe[i + stride:i + stride + 2] == b:
                found = i
                break
            i = exe.find(a, i + 1)
        print("   stride", stride, hex(found) if found is not None else None)

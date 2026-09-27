import struct
from pathlib import Path

exe = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe").read_bytes()
hit = 0xB936F0
# walk backwards while values look like ascending u16 codes
start = hit
while start >= 2:
    a = struct.unpack_from("<H", exe, start - 2)[0]
    b = struct.unpack_from("<H", exe, start)[0]
    if a < b:
        start -= 2
    else:
        break
end = hit
while end + 4 <= len(exe):
    a, b = struct.unpack_from("<HH", exe, end)
    if a < b:
        end += 2
    else:
        break
end += 2
n = (end - start) // 2
vals = struct.unpack_from(f"<{n}H", exe, start)
print(f"ascending run {start:#x}..{end:#x} = {n} codes, first {[hex(v) for v in vals[:12]]}, last {[hex(v) for v in vals[-6:]]}")
print("before run:", exe[start - 32:start].hex(" "))
print("after run:", exe[end:end + 32].hex(" "))
# where does 0x8144 sit in the run
print("index of 0x8144:", vals.index(0x8144) if 0x8144 in vals else None)
# look for other long ascending u16 runs (other languages' tables)
runs = []
i = 0
L = len(exe) - 2
while i < L:
    j = i
    while j + 4 <= len(exe) and struct.unpack_from("<H", exe, j)[0] < struct.unpack_from("<H", exe, j + 2)[0]:
        j += 2
    if (j - i) // 2 >= 1000:
        v = struct.unpack_from(f"<{(j - i)//2 + 1}H", exe, i)
        runs.append((i, len(v), hex(v[0]), hex(v[-1])))
        i = j + 2
    else:
        i += 2
for r in runs:
    print("run", hex(r[0]), r[1], r[2], r[3])

"""probe_string.py <build ver> <entry> <path...> : JP template / CHS original / built bytes (decoded) for one string."""
import sys
from pathlib import Path
from pc_idx import Archive, read_idx, decompress
from kt_text import walk
from ko_encode import decode
import json
from build_text import load_overrides

ROOT = Path(__file__).resolve().parents[1]
ver, e = sys.argv[1], int(sys.argv[2])
path = tuple(int(x) for x in sys.argv[3:])
bdir = ROOT / "build" / ver
idx = read_idx("CHS", bdir)
off, un, st, c = idx[e]
with open(bdir / "LINKFILE_CHS.BIN", "rb") as f:
    f.seek(off)
    blob = f.read(st)
built = decompress(blob, un)[0] if c else blob
get = lambda data: {s.path: s.raw for s in walk(data, "<")}
jp = get(Archive("JPN").read(e)).get(path)
chs = get(Archive("CHS").read(e)).get(path)
b = get(built).get(path)
print("JP   ", jp.decode("cp932", "replace") if jp else None)
print("CHS  ", chs.decode("gbk", "replace") if chs else None)
print("BUILT", decode(b) if b else None)
ov = load_overrides()
j = jp.decode("cp932", "replace") if jp else None
print("override:", ov.get(j))

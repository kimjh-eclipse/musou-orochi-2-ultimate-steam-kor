"""List every NUL-terminated string in an EXE range, classify JPN (CP932 with kana) / CHS (GBK) / ASCII.
usage: exe_tables.py <start hex> <end hex>"""
import sys
from pathlib import Path

EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
d = EXE.read_bytes()
a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)


def classify(raw):
    try:
        j = raw.decode("cp932")
        if any("\u3040" <= c <= "\u30ff" for c in j):
            return "JPN", j
    except UnicodeDecodeError:
        pass
    try:
        return ("CHS" if any(x >= 0x80 for x in raw) else "ASC"), raw.decode("gbk")
    except UnicodeDecodeError:
        return "???", raw.hex()


i = a
while i < b:
    if d[i] == 0:
        i += 1
        continue
    e = d.find(b"\0", i)
    raw = d[i:e]
    k, t = classify(raw)
    nxt = e
    while nxt < len(d) and d[nxt] == 0:
        nxt += 1
    print(f"{i:#x} {k} len={len(raw)} slot={nxt - i} {t[:60]!r}")
    i = e + 1

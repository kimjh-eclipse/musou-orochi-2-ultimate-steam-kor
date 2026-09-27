"""Pair the JPN and CHS message tables inside WO3U.exe (same order) and write translation_memory/exe_queue.jsonl.

Tables (file offsets, CHS table follows JPN, ENG, CHT copies of the same messages):
  unlimited-mode messages   JPN 0xac5970 x13  CHS 0xac5f98 x13
  help texts                JPN 0xac6170 x3   CHS 0xac68f0 x3
  dungeon/rebirth notices   JPN 0xac6af8 x11  CHS 0xac7410 x11
Each row: n, jp, chs, off (CHS string), slot (bytes available incl. the NUL terminator and padding).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
TABLES = [(0xAC5970, 0xAC5F98, 13), (0xAC6170, 0xAC68F0, 3), (0xAC6AF8, 0xAC7410, 11)]


def strings(d, off, n):
    out = []
    while len(out) < n:
        e = d.find(b"\0", off)
        nxt = e
        while d[nxt] == 0:
            nxt += 1
        out.append((off, d[off:e], nxt - off))
        off = nxt
    return out


def table(d):
    rows = []
    for jo, co, n in TABLES:
        for (jo_, jraw, _), (co_, craw, slot) in zip(strings(d, jo, n), strings(d, co, n)):
            rows.append({"n": len(rows), "off": co_, "slot": slot, "chs_len": len(craw),
                         "jp": jraw.decode("cp932").replace("\x1b", "⟨E⟩"),
                         "chs": craw.decode("gbk").replace("\x1b", "⟨E⟩")})
    return rows


if __name__ == "__main__":
    rows = table(EXE.read_bytes())
    with (ROOT / "translation_memory/exe_queue.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for r in rows:
        print(r["n"], hex(r["off"]), r["slot"], repr(r["jp"]))

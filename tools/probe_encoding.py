from pathlib import Path
from pc_lx import records

P = Path(__file__).resolve().parents[1] / "extract" / "probe"
for part in ("CHS", "JPN"):
    d = (P / f"{part}_00034.bin").read_bytes()
    rows = list(records(d))
    ok = {"utf-8": 0, "gbk": 0, "cp932": 0}
    for *_, raw in rows:
        for enc in ok:
            try:
                raw.decode(enc)
                ok[enc] += 1
            except UnicodeDecodeError:
                pass
    print(part, "records", len(rows), "decodable:", ok)
    for sec, i, p, o, raw in rows[1000:1008]:
        print("  ", i, raw[:40].hex(), "|", raw.decode("utf-8", "replace")[:40])

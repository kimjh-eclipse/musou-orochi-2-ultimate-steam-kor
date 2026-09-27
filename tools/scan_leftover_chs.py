"""Find Chinese (GBK hanzi) text left in the built CHS part outside the strings the text build rewrote.

For every used id: decompress the built entry, blank out the byte ranges of strings found by kt_text.walk,
then look for runs of >= MIN GBK hanzi (lead B0-F7, trail A1-FE, or GBK extension) in what remains.
Entries also replaced as images (G1T) are skipped. Output: extract/leftover_chs.json + summary.
"""
import json, re, sys
from pathlib import Path
from pc_idx import read_idx, decompress
from kt_text import walk

ROOT = Path(__file__).resolve().parents[1]
MIN = 3
ver = sys.argv[1]
bdir = ROOT / "build" / ver
idx = read_idx("CHS", bdir)
# GB2312 hanzi or GBK extension hanzi, optionally mixed with GBK punctuation / ASCII digits
HZ = rb"(?:[\xB0-\xF7][\xA1-\xFE]|[\x81-\xA0][\x40-\xFE]|[\xAA-\xFE][\x40-\xA0])"
RUN = re.compile(rb"(?:" + HZ + rb"|\xA1[\xA1-\xFE]|\xA3[\xA1-\xFE]){%d,}" % MIN)
out = []
with open(bdir / "LINKFILE_CHS.BIN", "rb") as f:
    for e, (off, un, st, c) in enumerate(idx):
        if not st:
            continue
        f.seek(off)
        blob = f.read(st)
        try:
            data = decompress(blob, un)[0] if c else blob
        except Exception:
            continue
        if data[:4] in (b"GT1G", b"G1TG"):
            continue
        buf = bytearray(data)
        try:
            for s in walk(data, "<"):
                buf[s.pos:s.pos + len(s.raw)] = b"\0" * len(s.raw)
        except Exception:
            pass
        hits = []
        for m in RUN.finditer(bytes(buf)):
            t = m.group().decode("gbk", "replace")
            if sum(1 for ch in t if "一" <= ch <= "鿿") >= MIN:
                hits.append((m.start(), t))
        if hits:
            out.append({"entry": e, "size": len(data), "magic": data[:8].hex(), "count": len(hits),
                        "samples": [h[1][:40] for h in hits[:6]], "first": hits[0][0]})
out.sort(key=lambda r: -r["count"])
(ROOT / "extract/leftover_chs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("entries with leftover Chinese:", len(out), "total runs:", sum(r["count"] for r in out))
for r in out[:40]:
    print(r["entry"], r["count"], r["magic"], r["samples"][:3])

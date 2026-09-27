"""Compose a line from atlas cells (48 px advance) of a build and of test01 to compare glyph fill."""
import json, sys
from pathlib import Path
from PIL import Image
from pc_idx import Archive
from ko_charset import table_codes

ROOT = Path(__file__).resolve().parents[1]
text = sys.argv[1]
cs = json.loads((ROOT / "mapping/ko_charset.json").read_text(encoding="utf-8"))["chars"]
cell = {c: k for k, c in enumerate(table_codes())}
rows = []
for ver in sys.argv[2:]:
    d = Archive("CHS", game=ROOT / "build" / ver).read(38)
    atlas = Image.frombytes("RGBA", (4096, 8192), d[0x38:0x38 + 4096 * 8192], "bcn", 3).getchannel("A")
    line = Image.new("L", (48 * len(text), 48))
    for i, ch in enumerate(text):
        if ch in cs:
            k = cell[int(cs[ch], 16)]
            line.paste(atlas.crop(((k % 85) * 48, (k // 85) * 48, (k % 85 + 1) * 48, (k // 85 + 1) * 48)), (i * 48, 0))
    rows.append(line)
out = Image.new("L", (rows[0].width, 52 * len(rows)))
for i, r in enumerate(rows):
    out.paste(r, (0, i * 52))
out.save(ROOT / "extract/probe/line_compare.png")

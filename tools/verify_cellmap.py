"""Check atlas cell k <-> EXE code table[k+1] by rendering sample cells next to a reference font glyph."""
import struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from font_grid import decode

EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
P = Path(__file__).resolve().parents[1] / "extract" / "probe"
TABLES = {"JPN": (0xA78A1E, 7372, "cp932"), "CHS": (0xB936EE, 9888, "gbk")}
exe = EXE.read_bytes()
ref = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 40)

for part, (off, n, enc) in TABLES.items():
    codes = struct.unpack_from(f"<{n}H", exe, off)
    arr = np.asarray(decode(part))
    inked = lambda k: (arr[(k // 85) * 48:(k // 85 + 1) * 48, (k % 85) * 48:(k % 85 + 1) * 48] > 40).any()
    real = n - 2
    empties = [k for k in range(real) if not inked(k)]
    print(part, "codes", real, "empty cells within table range:",
          [(k, hex(codes[k + 1])) for k in empties[:12]], "count", len(empties))
    beyond = [k for k in range(real, 85 * 170) if inked(k)]
    print("   inked cells beyond table:", len(beyond), beyond[:5], beyond[-3:])
    samples = [0, 1, 2, 500, 1000, 2000, 4000, 6000, real - 3, real - 2, real - 1]
    sheet = Image.new("L", (len(samples) * 50, 110), 0)
    d = ImageDraw.Draw(sheet)
    for j, k in enumerate(samples):
        cell = Image.fromarray(arr[(k // 85) * 48:(k // 85 + 1) * 48, (k % 85) * 48:(k % 85 + 1) * 48])
        sheet.paste(cell, (j * 50, 0))
        code = codes[k + 1]
        ch = struct.pack(">H", code).decode(enc, "replace") if code > 0xFF else chr(code)
        d.text((j * 50 + 4, 55), ch, font=ref, fill=255)
    sheet.save(P / f"{part}_cellmap_check.png")
    # the region beyond the table
    rows = sorted({k // 85 for k in beyond})
    if rows:
        Image.fromarray(arr[rows[0] * 48:(rows[-1] + 1) * 48, :]).save(P / f"{part}_beyond.png")
        print("   beyond rows", rows[0], "..", rows[-1])

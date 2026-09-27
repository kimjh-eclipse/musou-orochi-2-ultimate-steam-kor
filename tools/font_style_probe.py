from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from bc3 import decode_alpha_block, block_offset
from font_grid import decode

P = Path(__file__).resolve().parents[1] / "extract" / "probe"
raw = (P / "CHS_00038.bin").read_bytes()
arr = np.asarray(decode("CHS"))
# 1) decoder agreement on 2000 blocks
bad = 0
for n in range(2000):
    bx, by = (n * 37) % 1024, (n * 53) % 2048
    mine = decode_alpha_block(raw[block_offset(bx, by):block_offset(bx, by) + 8]).reshape(4, 4)
    ref = arr[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4]
    bad += int((mine != ref).any())
print("alpha decoder mismatching blocks:", bad, "/ 2000")
# 2) colour halves of glyph blocks
cols = {}
for n in range(4000):
    bx, by = (n * 37) % 1020, (n * 53) % 1000
    o = block_offset(bx, by)
    cols[raw[o + 8:o + 12].hex()] = cols.get(raw[o + 8:o + 12].hex(), 0) + 1
print("colour endpoint pairs (top):", sorted(cols.items(), key=lambda x: -x[1])[:6])

# 3) style sheet: CHS cells vs Noto Sans KR at weights
VF = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
chs_cells = [arr[r * 48:(r + 1) * 48, c * 48:(c + 1) * 48] for r, c in ((20, 3), (20, 4), (40, 10), (60, 20), (30, 30))]
text = "무쌍오로치한"
sheet = Image.new("L", (48 * 12, 48 * 6), 0)
for k, cell in enumerate(chs_cells):
    sheet.paste(Image.fromarray(cell), (k * 48, 0))
for row, (wname, size) in enumerate((("Regular", 42), ("Medium", 42), ("SemiBold", 42), ("Medium", 40), ("Bold", 42))):
    f = ImageFont.truetype(VF, size)
    try:
        f.set_variation_by_name(wname)
    except Exception as e:
        print("variation", wname, e)
    for k, ch in enumerate(text):
        g = Image.new("L", (48, 48), 0)
        d = ImageDraw.Draw(g)
        l, t, r, b = d.textbbox((0, 0), ch, font=f)
        d.text(((48 - (r - l)) / 2 - l, (48 - (b - t)) / 2 - t), ch, font=f, fill=255)
        sheet.paste(g, (k * 48, (row + 1) * 48))
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
sheet.save(P / "style_probe.png")
print(ImageFont.truetype(VF, 42).get_variation_names())

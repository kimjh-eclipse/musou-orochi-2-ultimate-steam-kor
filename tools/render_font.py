from pathlib import Path
from PIL import Image

P = Path(__file__).resolve().parents[1] / "extract" / "probe"
W, H, START = 4096, 8192, 0x38
d = (P / "CHS_00038.bin").read_bytes()
cw, ch = 512, 256
blk = d[START:]
# take the top 256 rows: 256/4=64 block-rows, each row W/4 blocks * 16 bytes
row_bytes = (W // 4) * 16
sub = b"".join(blk[r * row_bytes: r * row_bytes + (cw // 4) * 16] for r in range(ch // 4))
sheet = Image.new("RGBA", (cw * 3, ch * 2), (40, 40, 40, 255))
for n, bc in enumerate((2, 3, 5)):
    im = Image.frombytes("RGBA" if bc != 5 else "RGB", (cw, ch), sub, "bcn", bc).convert("RGBA")
    sheet.paste(im.convert("RGB").convert("RGBA"), (n * cw, 0))
    sheet.paste(Image.merge("RGBA", [im.getchannel("A")] * 3 + [Image.new("L", im.size, 255)]), (n * cw, ch))
sheet.save(P / "CHS_font_bc_trials.png")


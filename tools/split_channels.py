from pathlib import Path
from PIL import Image

P = Path(__file__).resolve().parents[1] / "extract" / "probe"
img = Image.open(P / "CHS_font.png")
crop = img.crop((0, 0, 512, 256))
sheet = Image.new("L", (1024, 512))
for n, ch in enumerate("RGBA"):
    sheet.paste(crop.getchannel(ch), ((n % 2) * 512, (n // 2) * 256))
sheet.save(P / "CHS_font_channels.png")

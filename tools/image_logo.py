"""Place an opaque-on-black artwork (the PS3 Korean title logo) into a transparent texture.

alpha = brightest channel (black background -> transparent, glows stay semi-transparent), colour un-premultiplied;
a soft dark halo behind the letters mimics the original logo's shadow. Fitted into `rect` keeping aspect."""
import numpy as np
from PIL import Image, ImageFilter


def luma_alpha(src, gain=1.6, floor=10):
    a = np.asarray(src.convert("RGB")).astype(np.float32)
    m = a.max(axis=2)
    alpha = np.clip((m - floor) * gain, 0, 255)
    safe = np.maximum(alpha, 1) / 255.0
    rgb = np.clip(a / safe[..., None], 0, 255)
    out = np.dstack([rgb, alpha]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def place_logo_over(picture, src_path, rect, erase, blur=28, grow=1.0):
    """Logo baked into an opaque picture: the old logo area `erase` is replaced by a heavily blurred copy of
    the picture (feathered ellipse), then the Korean logo is composited on top, fitted into `rect`."""
    x0, y0, x1, y1 = erase
    pic = picture.convert("RGBA")
    soft = pic.filter(ImageFilter.GaussianBlur(blur))
    mask = Image.new("L", pic.size, 0)
    from PIL import ImageDraw
    pad = int(max(x1 - x0, y1 - y0) * 0.08)
    ImageDraw.Draw(mask).ellipse((x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(pad * 0.6 + 4))
    base = Image.composite(soft, pic, mask)
    if grow != 1.0:
        cx, cy, hw, hh = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2, (rect[2] - rect[0]) / 2 * grow, (rect[3] - rect[1]) / 2 * grow
        rect = [int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh)]
    layer, rep = place_logo(base, src_path, rect)
    return Image.alpha_composite(base, layer), rep


def place_logo(texture, src_path, rect, shadow=0.75):
    src = Image.open(src_path).convert("RGB")
    bb = src.convert("L").point(lambda v: 255 if v > 24 else 0).getbbox()
    src = src.crop(bb)
    x0, y0, x1, y1 = rect
    W, H = x1 - x0 + 1, y1 - y0 + 1
    s = min(W / src.width, H / src.height)
    size = (max(1, int(src.width * s)), max(1, int(src.height * s)))
    logo = luma_alpha(src.resize(size, Image.Resampling.LANCZOS))
    out = Image.new("RGBA", texture.size, (0, 0, 0, 0))
    ox, oy = x0 + (W - size[0]) // 2, y0 + (H - size[1]) // 2
    a = logo.getchannel("A")
    halo = a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * shadow))
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    sh.putalpha(halo)
    out.alpha_composite(sh, (ox, oy))
    out.alpha_composite(logo, (ox, oy))
    return out, {"src": str(src_path), "placed": [ox, oy, ox + size[0] - 1, oy + size[1] - 1], "scale": round(s, 4)}

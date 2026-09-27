"""Redraw text labels of a label-atlas texture in Korean, matching the original label's colours.

Per label: the original box is cleared (padded, never into another label's box), the Korean text is
drawn in NotoSerifKR (Black, forward lean) with
  - fill: per-row colour gradient sampled from the original opaque ink,
  - glow/outline: dilated + blurred mask in the colour of the original semi-transparent edge pixels,
fitted to the box height, condensed horizontally down to 70 % and only then shrunk.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SERIF = r"C:\Windows\Fonts\NotoSerifKR-VF.ttf"
SANS = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"


def sample_style(im, box):
    x0, y0, x1, y1 = box
    a = np.asarray(im.crop((x0, y0, x1 + 1, y1 + 1))).astype(np.float32)
    alpha = a[..., 3]
    rgb = a[..., :3]
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    amax = float(alpha.max()) if alpha.size else 255.0
    # "ink" = the label's own solid pixels; semi-transparent captions never reach alpha 230
    opaque = alpha >= min(230, amax * 0.85)
    h = alpha.shape[0]
    if opaque.sum() > 50:
        hi_t = np.percentile(lum[opaque], 70)
        lo_t = np.percentile(lum[opaque], 10)
    else:
        hi_t = lo_t = 0
    fill_px = opaque & (lum >= hi_t)
    dark_px = opaque & (lum <= lo_t)
    edge = (alpha > 30) & (alpha < 200)
    grad = []
    fallback = np.median(rgb[fill_px], axis=0) if fill_px.any() else np.array([255, 255, 255])
    for k in range(8):
        r0, r1 = k * h // 8, (k + 1) * h // 8
        sel = fill_px[r0:r1]
        grad.append(np.median(rgb[r0:r1][sel], axis=0) if sel.sum() > 20 else fallback)
    outline = np.median(rgb[dark_px], axis=0) if dark_px.sum() > 20 else np.array([30, 24, 30])
    # an outline only if the dark opaque pixels are clearly darker than the fill
    has_outline = bool(dark_px.sum() > 20 and (np.mean(fallback) - np.mean(outline)) > 60)
    glow = np.median(rgb[edge], axis=0) if edge.sum() > 20 else outline
    glow_a = float(np.percentile(alpha[edge], 75)) / 255 if edge.sum() > 20 else 0.6
    ys = np.nonzero(opaque.any(axis=1))[0]
    ink_h = int(ys.max() - ys.min() + 1) if len(ys) else h
    yl = np.nonzero((alpha > 12).any(axis=1))[0]
    border = max(1, int(round(((yl.max() - yl.min() + 1) - ink_h) / 2))) if len(ys) and len(yl) else 2
    fill_a = float(np.percentile(alpha[opaque], 60)) / 255 if opaque.sum() > 50 else 1.0
    return {"grad": [g.tolist() for g in grad], "glow": glow.tolist(), "glow_a": glow_a,
            "outline": outline.tolist(), "has_outline": has_outline, "fill_a": fill_a,
            "ink_h": ink_h, "border": border}


def text_mask(text, px, font=SERIF, weight=800, shear=0.14, sx=1.0):
    ss = 3
    f = ImageFont.truetype(font, px * ss)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    l, t, r, b = f.getbbox(text)
    im = Image.new("L", (r - l + 8 * ss, b - t + 8 * ss))
    ImageDraw.Draw(im).text((4 * ss - l, 4 * ss - t), text, font=f, fill=255)
    if shear:
        w, h = im.size
        im = im.transform((w + int(h * shear) + 2, h), Image.Transform.AFFINE,
                          (1, shear, -h * shear, 0, 1, 0), Image.Resampling.BICUBIC)
    bb = im.getbbox()
    im = im.crop(bb)
    w = max(1, round(im.width * sx / ss))
    return im.resize((w, max(1, round(im.height / ss))), Image.Resampling.LANCZOS)


def first_big_mask(text, px, small=0.68, **kw):
    """First syllable at full size, the rest at `small`, bottoms aligned (the header-title style)."""
    a = text_mask(text[0], px, **kw)
    if len(text) == 1:
        return a
    b = text_mask(text[1:].lstrip(), max(8, int(px * small)), **kw)
    gap = max(1, px // 14)
    w, h = a.width + gap + b.width, max(a.height, b.height)
    m = Image.new("L", (w, h))
    m.paste(a, (0, h - a.height))
    m.paste(b, (a.width + gap, h - b.height - max(0, int(a.height * 0.02))))
    return m


def fit_mask(text, max_w, target_h, first_big=False, **kw):
    if first_big:
        px = max(8, int(target_h * 1.12))
        for _ in range(60):
            m = first_big_mask(text, px, **kw)
            if m.height > target_h * 1.02:
                px = max(8, int(px * target_h / m.height))
                m = first_big_mask(text, px, **kw)
            if m.width <= max_w:
                return m, 1.0
            sx = max_w / m.width
            if sx >= 0.72:
                return m.resize((max(1, int(m.width * sx)), m.height), Image.Resampling.LANCZOS), sx
            px = int(px * 0.95)
            target_h *= 0.95
        return m, 1.0
    return _fit_plain(text, max_w, target_h, **kw)


def _fit_plain(text, max_w, target_h, **kw):
    px = max(8, int(target_h * 1.12))
    for _ in range(60):
        m = text_mask(text, px, **kw)
        # scale font so ink height ~ target_h
        if m.height > target_h * 1.02:
            px = max(8, int(px * target_h / m.height))
            m = text_mask(text, px, **kw)
        if m.width <= max_w:
            return m, 1.0
        sx = max_w / m.width
        if sx >= 0.70:
            return text_mask(text, px, sx=sx, **kw), sx
        px = int(px * 0.95)
        target_h = target_h * 0.95
    return m, 1.0


def _shift(mask, dx, dy):
    s = Image.new("L", mask.size)
    s.paste(mask, (dx, dy))
    return s


def render_label(text, size, style, align="left", font=SERIF, shear=0.14, first_big=False):
    W, H = size
    b = style["border"]
    m, sx = fit_mask(text, W - 2 * b, min(style["ink_h"], H - 2 * b), first_big=first_big, font=font, shear=shear)
    mask = Image.new("L", size)
    x = b if align == "left" else (W - m.width) // 2 if align == "center" else W - b - m.width
    y = (H - m.height) // 2
    mask.paste(m, (x, y))
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    glow = mask.filter(ImageFilter.MaxFilter(2 * max(1, b // 2) + 1)).filter(ImageFilter.GaussianBlur(max(1, b * 0.6)))
    gl = Image.new("RGBA", size, tuple(int(c) for c in style["glow"]) + (0,))
    gl.putalpha(glow.point(lambda v: int(v * style["glow_a"])))
    out = Image.alpha_composite(out, gl)
    ol_w = max(1, round(m.height * 0.025))
    if style.get("has_outline"):
        ol = mask.filter(ImageFilter.MaxFilter(2 * ol_w + 1))
        layer = Image.new("RGBA", size, tuple(int(c) for c in style["outline"]) + (0,))
        layer.putalpha(ol)
        out = Image.alpha_composite(out, layer)
    # drop shadow toward the lower right, in the outline colour, gives the embossed look of the originals
    sh = Image.new("L", size)
    sh.paste(mask, (ol_w, ol_w))
    layer = Image.new("RGBA", size, tuple(int(c * 0.6) for c in style["outline"]) + (0,))
    layer.putalpha(sh.point(lambda v: int(v * 0.85)))
    out = Image.alpha_composite(out, layer)
    fill = Image.new("RGBA", size)
    dr = ImageDraw.Draw(fill)
    g = style["grad"]
    for yy in range(H):
        t = min(1, max(0, (yy - y) / max(1, m.height - 1))) * (len(g) - 1)
        k = min(int(t), len(g) - 2)
        f = t - k
        c = [int(g[k][i] * (1 - f) + g[k + 1][i] * f) for i in range(3)]
        dr.line((0, yy, W, yy), fill=tuple(c) + (255,))
    fill.putalpha(mask.point(lambda v: int(v * style.get("fill_a", 1.0))))
    out = Image.alpha_composite(out, fill)
    # thin highlight on the upper-left edges
    from PIL import ImageChops
    edge = ImageChops.subtract(mask, _shift(mask, 1, 1))
    top = [min(255, int(c * 1.15 + 20)) for c in g[0]]
    layer = Image.new("RGBA", size, tuple(top) + (0,))
    layer.putalpha(edge.point(lambda v: int(v * 0.5)))
    out = Image.alpha_composite(out, layer)
    return out, {"text": text, "condense": round(sx, 3), "ink": list(m.size)}


def apply_labels(im, labels, pad_frac=0.12):
    """labels: [{box:[x0,y0,x1,y1], ko:str, extend_w?:int, align?}] -> new image, report."""
    out = im.copy()
    arr = np.asarray(out).copy()
    boxes = [l["box"] for l in labels]
    W, H = im.size
    rep = []
    for i, l in enumerate(labels):
        x0, y0, x1, y1 = l["box"]
        pad = l["pad"] if "pad" in l else max(2, int((y1 - y0) * pad_frac))
        cx0, cy0, cx1, cy1 = max(0, x0 - pad), max(0, y0 - pad), min(W - 1, x1 + pad), min(H - 1, y1 + pad)
        # do not clear into other labels
        for j, (a0, b0, a1, b1) in enumerate(boxes):
            if j == i or a1 < cx0 or a0 > cx1 or b1 < cy0 or b0 > cy1:
                continue
            if b1 < y0:
                cy0 = max(cy0, b1 + 1)
            elif b0 > y1:
                cy1 = min(cy1, b0 - 1)
            elif a1 < x0:
                cx0 = max(cx0, a1 + 1)
            elif a0 > x1:
                cx1 = min(cx1, a0 - 1)
        if l.get("erase") == "solid":
            # text on an opaque flat background (e.g. black intro card): paint the background colour back
            arr[cy0:cy1 + 1, cx0:cx1 + 1] = l["bg"]
            rep.append({"clear": [cx0, cy0, cx1, cy1]})
            continue
        if l.get("erase") == "rowfill":
            # text on a horizontally uniform button face: find the text span (bright glyphs + outline margin)
            # and repaint every row of it by interpolating the button pixels just left and right of the span
            sub = arr[y0:y1 + 1, x0:x1 + 1].astype(np.float64)
            lum = sub[..., :3] @ np.array([0.299, 0.587, 0.114])
            lit = (lum > l.get("lum", 170)) & (sub[..., 3] > 100)
            cols = np.nonzero(lit.any(0))[0]
            if len(cols):
                g = l.get("ink_grow", 4)
                a0, a1 = max(1, cols.min() - g), min(sub.shape[1] - 2, cols.max() + g)
                left = sub[:, max(0, a0 - 3):a0].mean(1)
                right = sub[:, a1 + 1:a1 + 4].mean(1)
                n = a1 - a0 + 1
                w = np.linspace(0, 1, n)[None, :, None]
                sub[:, a0:a1 + 1] = left[:, None, :] * (1 - w) + right[:, None, :] * w
                arr[y0:y1 + 1, x0:x1 + 1] = np.clip(sub, 0, 255).astype(np.uint8)
            rep.append({"clear": [x0, y0, x1, y1]})
            continue
        if l.get("erase") == "bright":
            # light text printed on button/panel art: fill the glyphs from their row neighbours, keep the art
            from image_overpaint import fill
            ix = int((x1 - x0 + 1) * l.get("inset_x", 0.0))
            ax0, ax1 = x0 + ix, x1 - ix
            sub = arr[y0:y1 + 1, ax0:ax1 + 1].astype(np.float64)
            lum = sub[..., :3] @ np.array([0.299, 0.587, 0.114])
            m = (lum > l.get("lum", 170)) & (sub[..., 3] > 100)
            m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(
                ImageFilter.MaxFilter(2 * l.get("ink_grow", 2) + 1))) > 0
            arr[y0:y1 + 1, ax0:ax1 + 1] = np.clip(fill(sub, m, kx=l.get("kx", 12), ky=1), 0, 255).astype(np.uint8)
            rep.append({"clear": [x0, y0, x1, y1]})
            continue
        if l.get("erase") == "ink":
            # the label sits on an ornament: remove only the solid text + its outline, keep the soft backdrop
            sub = Image.fromarray(((arr[cy0:cy1 + 1, cx0:cx1 + 1, 3] >= l.get("ink_a", 150)) * 255).astype(np.uint8))
            grow = l.get("ink_grow", 3)
            m = np.asarray(sub.filter(ImageFilter.MaxFilter(2 * grow + 1))) > 0
            arr[cy0:cy1 + 1, cx0:cx1 + 1][m] = 0
        else:
            arr[cy0:cy1 + 1, cx0:cx1 + 1] = 0
        rep.append({"clear": [cx0, cy0, cx1, cy1]})
    out = Image.fromarray(arr, "RGBA")
    for l, r in zip(labels, rep):
        x0, y0, x1, y1 = l["box"]
        if l.get("grow"):
            cx, half = (x0 + x1) / 2, (x1 - x0 + 1) * l["grow"] / 2
            x0, x1 = max(0, int(cx - half)), min(W - 1, int(cx + half))
            r["clear"] = [min(r["clear"][0], x0), r["clear"][1], max(r["clear"][2], x1), r["clear"][3]]
        style = l.get("style") or sample_style(im, l["box"])
        if l.get("angle"):
            # tilted stamp text: lay the line out flat along the box diagonal, rotate, centre on the box
            import math
            bw, bh = x1 - x0 + 1, y1 - y0 + 1
            ang = l["angle"]
            L = int(math.hypot(bw, bh) * l.get("len_frac", 0.92))
            th = int(l.get("line_h", min(bw, bh) * 0.42))
            st = dict(style, ink_h=int(th * 0.8), border=max(2, th // 12))
            patch, info = render_label(l["ko"], (L, th), st, "center", font=l.get("font", SERIF),
                                       shear=l.get("shear", 0.14))
            patch = patch.rotate(ang, resample=Image.Resampling.BICUBIC, expand=True)
            layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
            layer.paste(patch, ((x0 + x1) // 2 - patch.width // 2, (y0 + y1) // 2 - patch.height // 2), patch)
            out = Image.alpha_composite(out, layer)
            r.update(info)
            continue
        w = l.get("extend_w") or (x1 - x0 + 1)
        cx0, cy0, cx1, cy1 = r["clear"]
        w = min(w, cx1 - x0 + 1)
        patch, info = render_label(l["ko"], (w, y1 - y0 + 1), style, l.get("align", "left"),
                                   font=l.get("font", SERIF), shear=l.get("shear", 0.14),
                                   first_big=l.get("first_big", False))
        out.alpha_composite(patch, (x0, y0))
        r.update(info)
    return out, rep

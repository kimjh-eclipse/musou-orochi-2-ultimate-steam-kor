"""Replace text baked into an opaque picture (loading-screen name cards).

Every language slot has its caption at the same place, so the true background cannot be recovered.
The caption (bright glyphs found by CHS-vs-JPN difference, grown to cover the drop shadow) is filled by a
normalized convolution with a wide, flat kernel: horizontal features such as the purple swoosh line carry
through, and no blotches appear. Korean is then drawn with image_labels.render_label using a style sampled
from the CHS caption.
"""
import numpy as np
from PIL import Image, ImageFilter
from image_labels import render_label, sample_style, SERIF


def _dilate(m, r):
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * r + 1))
    return np.asarray(im) > 0


def _box(a, kx, ky):
    """Separable box filter via cumulative sums (edges clamped)."""
    def run(x, k, axis):
        pad = [(0, 0)] * x.ndim
        pad[axis] = (k, k)
        p = np.pad(x, pad, mode="edge")
        c = np.cumsum(p, axis=axis, dtype=np.float64)
        n = x.shape[axis]
        hi = np.take(c, np.arange(2 * k, 2 * k + n), axis=axis)
        lo = np.take(c, np.arange(0, n), axis=axis)
        return (hi - lo) / (2 * k)
    return run(run(a, kx, 1), ky, 0)


def fill(rgb, hole, kx=60, ky=4):
    known = (~hole).astype(np.float64)
    out = rgb.astype(np.float64).copy()
    todo = hole.copy()
    for s in (1, 2, 4, 8):
        num = _box(out * known[..., None], kx * s, ky * s)
        den = _box(known, kx * s, ky * s)
        ok = todo & (den > 0.05)
        out[ok] = num[ok] / den[ok][:, None]
        todo &= ~ok
        if not todo.any():
            break
    return out


def _longest_run(flags, gap):
    best, cur, start, last = (0, 0, -1), None, None, None
    idx = np.nonzero(flags)[0]
    runs, s, p = [], None, None
    for i in idx:
        if s is None:
            s = p = i
        elif i - p <= gap:
            p = i
        else:
            runs.append((s, p))
            s = p = i
    if s is not None:
        runs.append((s, p))
    return max(runs, key=lambda r: flags[r[0]:r[1] + 1].sum()) if runs else None


def caption_core(chs, jpn, region, thr=36):
    x0, y0, x1, y1 = region
    a = np.asarray(chs.convert("RGB"))[y0:y1, x0:x1].astype(np.int16)
    b = np.asarray(jpn.convert("RGB"))[y0:y1, x0:x1].astype(np.int16)
    la, lb = a.mean(-1), b.mean(-1)
    diff = np.abs(a - b).max(-1) > thr
    return a, diff & (la > lb + thr) & (la > 150)


def overpaint(chs, jpn, region, ko, font=SERIF, first_big=True, extend=1.7, shear=0.1, grow=12):
    x0, y0, x1, y1 = region
    a, cc = caption_core(chs, jpn, region)
    if cc.sum() < 200:
        return chs, {"text": ko, "condense": None, "note": "no caption found"}
    r = _longest_run(cc.sum(1) > max(2, cc.sum(1).max() * 0.04), 12)
    c = _longest_run(cc[r[0]:r[1] + 1].sum(0) > 0, 40)
    box = [x0 + int(c[0]), y0 + int(r[0]), x0 + int(c[1]), y0 + int(r[1])]
    style = sample_style(chs.convert("RGBA"), box)
    core = np.zeros_like(cc)
    core[r[0]:r[1] + 1, c[0]:c[1] + 1] = cc[r[0]:r[1] + 1, c[0]:c[1] + 1]
    # the drop shadow sits below-right of the glyphs: grow the hole more in that direction
    hole = _dilate(core, grow)
    hole |= np.roll(np.roll(hole, grow // 2, 0), grow // 2, 1)
    bg = fill(a, hole)
    # feather the patch edge so the flat fill does not show a rectangular seam
    soft = np.asarray(Image.fromarray((hole * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float64) / 255
    soft = np.maximum(soft, _dilate(core, grow // 2))[..., None]
    bg = a * (1 - soft) + bg * soft
    out = chs.convert("RGBA").copy()
    out.paste(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA"), (x0, y0))
    w = min(int((box[2] - box[0] + 1) * extend), chs.width - box[0] - 8)
    patch, info = render_label(ko, (w, box[3] - box[1] + 1), style, "left", font=font, shear=shear, first_big=first_big)
    out.alpha_composite(patch, (box[0], box[1]))
    info.update({"box": box})
    return out, info

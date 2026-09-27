"""Find text-label boxes in a label-atlas texture from its alpha: rows split on empty scanlines, then each
row split on horizontal gaps wider than `gap` * row height. Writes a numbered preview.
usage: label_boxes.py <entry> <tex> [gap]"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from pc_idx import Archive
from g1t_pc import parse, decode

ROOT = Path(__file__).resolve().parents[1]


def boxes(alpha, gap=0.6, thr=12, core=128):
    """Rows/segments are found on the opaque core (alpha > core) so touching glows do not merge lines;
    each box is then grown to the soft extent (alpha > thr) inside its own row band."""
    raw = boxes_at(alpha, gap, core)
    soft = alpha > thr
    H, W = alpha.shape
    out = []
    for k, (x0, y0, x1, y1) in enumerate(raw):
        g = max(2, (y1 - y0) // 6)
        a0, b0, a1, b1 = max(0, x0 - g), max(0, y0 - g), min(W - 1, x1 + g), min(H - 1, y1 + g)
        sub = soft[b0:b1 + 1, a0:a1 + 1]
        ys, xs = np.nonzero(sub)
        out.append([a0 + int(xs.min()), b0 + int(ys.min()), a0 + int(xs.max()), b0 + int(ys.max())])
    # grown boxes of neighbouring rows must not overlap: split the overlap in the middle
    for i in range(len(out)):
        for j in range(len(out)):
            if i == j:
                continue
            A, B = out[i], out[j]
            if A[3] >= B[1] and A[1] < B[1] and not (A[2] < B[0] or B[2] < A[0]):
                mid = (raw[i][3] + raw[j][1]) // 2
                A[3] = min(A[3], mid)
                B[1] = max(B[1], mid + 1)
    return out


def boxes_at(alpha, gap=0.6, thr=12):
    a = alpha > thr
    rows = a.any(axis=1)
    out = []
    y = 0
    H = len(rows)
    while y < H:
        if not rows[y]:
            y += 1
            continue
        y0 = y
        while y < H and rows[y]:
            y += 1
        y1 = y - 1
        if y1 - y0 < 3:
            continue
        cols = a[y0:y1 + 1].any(axis=0)
        xs = np.nonzero(cols)[0]
        h = y1 - y0 + 1
        seg = [xs[0]]
        prev = xs[0]
        for x in xs[1:]:
            if x - prev > gap * h:
                out.append([int(seg[0]), y0, int(prev), y1])
                seg = [x]
            prev = x
        out.append([int(seg[0]), y0, int(prev), y1])
    return out


def load(e, ti, part="CHS"):
    d = Archive(part).read(e)
    t = parse(d)["tex"][ti]
    return d, t, decode(d, t)


if __name__ == "__main__":
    e, ti = int(sys.argv[1]), int(sys.argv[2])
    gap = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    d, t, im = load(e, ti)
    bx = boxes(np.asarray(im.getchannel("A")), gap)
    prev = Image.new("RGBA", im.size, (40, 44, 60, 255))
    prev.alpha_composite(im)
    dr = ImageDraw.Draw(prev)
    for k, (x0, y0, x1, y1) in enumerate(bx):
        dr.rectangle((x0, y0, x1, y1), outline=(0, 255, 0, 255))
        dr.text((x0 + 2, y0 + 2), str(k), fill=(255, 255, 0, 255))
    bb = im.getchannel("A").getbbox()
    prev = prev.crop(bb) if bb else prev
    s = min(1.0, 1400 / max(prev.size))
    prev = prev.resize((int(prev.width * s), int(prev.height * s)))
    prev.save(ROOT / f"extract/probe/boxes_{e}_t{ti}.png")
    print(json.dumps(bx))

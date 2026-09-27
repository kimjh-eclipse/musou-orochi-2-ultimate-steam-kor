"""Label boxes by connected components (for atlases whose lines are staggered, where row splitting fails).
Core = alpha > core; glyphs of one word are joined by a horizontal smear of kx px (vertical ky px).
usage: cc_boxes.py <entry> <tex> [kx] [ky] -> numbered tiles like box_index_view.py"""
import sys
from collections import deque
import numpy as np


def cc_boxes(alpha, kx=14, ky=2, core=128, soft=12, step=2):
    m = alpha[::step, ::step] > core
    g = m.copy()
    for s in range(1, kx // step + 1):
        g[:, s:] |= m[:, :-s]
        g[:, :-s] |= m[:, s:]
    h = g.copy()
    for s in range(1, ky // step + 1):
        h[s:] |= g[:-s]
        h[:-s] |= g[s:]
    H, W = h.shape
    seen = np.zeros_like(h)
    out = []
    for y, x in zip(*np.nonzero(h)):
        if seen[y, x]:
            continue
        q = deque([(y, x)])
        seen[y, x] = 1
        pts = []
        while q:
            cy, cx = q.popleft()
            pts.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < H and 0 <= nx < W and h[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = 1
                    q.append((ny, nx))
        p = np.array(pts)
        sel = m[p[:, 0], p[:, 1]]
        if sel.sum() < 6:
            continue
        cp = p[sel] * step
        y0, x0 = cp.min(0)
        y1, x1 = cp.max(0) + step - 1
        out.append([int(x0), int(y0), int(x1), int(y1)])
    # grow to the soft extent, sort row-major by centre line
    A = alpha > soft
    res = []
    for x0, y0, x1, y1 in out:
        gy = max(2, (y1 - y0) // 8)
        a0, b0, a1, b1 = max(0, x0 - gy), max(0, y0 - gy), min(alpha.shape[1] - 1, x1 + gy), min(alpha.shape[0] - 1, y1 + gy)
        ys, xs = np.nonzero(A[b0:b1 + 1, a0:a1 + 1])
        res.append([a0 + int(xs.min()), b0 + int(ys.min()), a0 + int(xs.max()), b0 + int(ys.max())])
    res.sort(key=lambda b: (round(((b[1] + b[3]) / 2) / 20), b[0]))
    return res


if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image, ImageDraw
    from label_boxes import load
    ROOT = Path(__file__).resolve().parents[1]
    e, ti = int(sys.argv[1]), int(sys.argv[2])
    kx = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    ky = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    d, t, im = load(e, ti)
    core = int(sys.argv[5]) if len(sys.argv) > 5 else 128
    bx = cc_boxes(np.asarray(im.getchannel("A")), kx, ky, core=core)
    bg = Image.new("RGBA", im.size, (30, 34, 48, 255))
    bg.alpha_composite(im)
    dr = ImageDraw.Draw(bg)
    for i, b in enumerate(bx):
        dr.rectangle(b, outline=(255, 60, 60, 255))
        dr.rectangle((b[0], b[1], b[0] + 26, b[1] + 14), fill=(0, 0, 0, 255))
        dr.text((b[0] + 2, b[1] + 1), str(i), fill=(255, 255, 0, 255))
    bb = im.getchannel("A").getbbox()
    n = 0
    for y in range(bb[1], bb[3], 600):
        for x in range(bb[0], bb[2], 1400):
            bg.crop((x, y, x + 1400, y + 600)).save(ROOT / f"extract/peek/cc_{e}_{ti}_{n}.png")
            n += 1
    print(len(bx), "boxes", n, "tiles")

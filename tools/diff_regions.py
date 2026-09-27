"""diff_regions.py e:t ... : bounding boxes of CHS-vs-JPN pixel differences (connected by 24px dilation)."""
import sys
import numpy as np
from PIL import Image, ImageFilter
from pc_idx import Archive
from g1t_pc import parse, decode

chs, jpn = Archive("CHS"), Archive("JPN")
for it in sys.argv[1:]:
    e, ti = map(int, it.split(":"))
    a = np.asarray(decode(chs.read(e), parse(chs.read(e))["tex"][ti])).astype(int)
    dj = jpn.read(e)
    tj = parse(dj)["tex"][ti]
    b = np.asarray(decode(dj, tj)).astype(int)
    if a.shape != b.shape:
        print(it, "size differs", a.shape, b.shape)
        continue
    m = (np.abs(a - b).max(-1) > 48) & ((a[..., 3] > 30) | (b[..., 3] > 30))
    g = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(25))) > 0
    # label connected blobs by scanning rows/cols of the dilated mask
    from collections import deque
    seen = np.zeros_like(g)
    out = []
    H, W = g.shape
    ys, xs = np.nonzero(g[::4, ::4])
    for y, x in zip(ys * 4, xs * 4):
        if seen[y, x] or not g[y, x]:
            continue
        q = deque([(y, x)]); seen[y, x] = 1
        y0 = y1 = y; x0 = x1 = x; n = 0
        while q:
            cy, cx = q.popleft(); n += 1
            y0, y1, x0, x1 = min(y0, cy), max(y1, cy), min(x0, cx), max(x1, cx)
            for ny, nx in ((cy + 4, cx), (cy - 4, cx), (cy, cx + 4), (cy, cx - 4)):
                if 0 <= ny < H and 0 <= nx < W and g[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = 1; q.append((ny, nx))
        if n > 20:
            out.append((x0, y0, x1, y1, n))
    out.sort(key=lambda r: -r[4])
    print(it, (tj["w"], tj["h"]), out[:6])

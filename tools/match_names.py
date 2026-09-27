"""match_names.py <entry> <tex> [x0 y0 x1 y1] : identify name boxes by shape against the hand-read atlases
(6051 t5/t6 from spec_names2.K, 6054 t0-t2). Prints per-box best k, score and margin to the runner-up."""
import sys
import numpy as np
from PIL import Image
from label_boxes import boxes, load
from spec_names import NAME

sys_argv = sys.argv[:]
from spec_names2 import K  # noqa: E402  (re-writes 06051.json deterministically)


def sig(a, box, W=128, H=32):
    x0, y0, x1, y1 = box
    c = a[y0:y1 + 1, x0:x1 + 1] > 128
    ys, xs = np.nonzero(c)
    if len(xs):
        c = c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        x0, y0, x1, y1 = 0, 0, c.shape[1] - 1, c.shape[0] - 1
    im = Image.fromarray(c.astype(np.uint8) * 255)
    v = np.asarray(im.resize((W, H), Image.Resampling.BOX), np.float32).ravel()
    v -= v.mean()
    return v / (np.linalg.norm(v) or 1), (x1 - x0 + 1) / (y1 - y0 + 1)


def reference():
    ref = []
    for ti, ks in K.items():
        d, t, im = load(6051, ti)
        a = np.asarray(im.getchannel("A"))
        for b, k in zip(boxes(a, gap=0.2), ks):
            ref.append((k,) + sig(a, b))
    for ti, ks in ((0, range(0, 110)), (1, range(110, 137)), (2, range(137, 145))):
        d, t, im = load(6054, ti)
        a = np.asarray(im.getchannel("A"))
        for b, k in zip(boxes(a), ks):
            ref.append((k,) + sig(a, b))
    return ref


def match(a, bx, ref):
    R = np.stack([r[1] for r in ref])
    RA = np.array([r[2] for r in ref])
    out = []
    for b in bx:
        s, asp = sig(a, b)
        sc = R @ s - 0.5 * np.abs(np.log(RA / asp))
        best = {}
        for (k, _, _), v in zip(ref, sc):
            best[k] = max(best.get(k, -9), v)
        o = sorted(best.items(), key=lambda kv: -kv[1])
        out.append((b, o[0][0], round(float(o[0][1]), 3), o[1][0], round(float(o[0][1] - o[1][1]), 3)))
    return out


if __name__ == "__main__":
    e, ti = int(sys_argv[1]), int(sys_argv[2])
    d, t, im = load(e, ti)
    a = np.asarray(im.getchannel("A"))
    if len(sys_argv) > 6:
        x0, y0, x1, y1 = map(int, sys_argv[3:7])
        sub = np.zeros_like(a)
        sub[y0:y1, x0:x1] = a[y0:y1, x0:x1]
        a = sub
    bx = boxes(a, gap=0.2)
    res = match(a, bx, reference())
    weak = [r for r in res if r[2] < 0.85 or r[4] < 0.04]
    print(len(res), "boxes, weak", len(weak))
    for r in weak[:40]:
        print("  ", r[0], NAME[r[1]], r[2], NAME[r[3]], r[4])

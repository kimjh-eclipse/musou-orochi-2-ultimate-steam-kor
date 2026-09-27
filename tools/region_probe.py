"""region_probe.py <entry> <tex> x0 y0 x1 y1 [gap] : label boxes (label_boxes.boxes) inside a region, full-res coords."""
import sys
import numpy as np
from label_boxes import boxes, load

e, ti, x0, y0, x1, y1 = map(int, sys.argv[1:7])
gap = float(sys.argv[7]) if len(sys.argv) > 7 else 0.6
d, t, im = load(e, ti)
a = np.asarray(im.getchannel("A"))[y0:y1, x0:x1]
for b in boxes(a, gap=gap):
    print([b[0] + x0, b[1] + y0, b[2] + x0, b[3] + y0])

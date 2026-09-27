import numpy as np
from PIL import Image
from pathlib import Path
from pc_idx import Archive, used_ids
from font_grid import decode

P = Path(__file__).resolve().parents[1] / "extract" / "probe"
for part in ("CHS", "JPN"):
    arr = np.asarray(decode(part))[:170 * 48, :85 * 48]
    cells = arr.reshape(170, 48, 85, 48).swapaxes(1, 2)  # rows, cols, 48, 48
    ink = (cells > 40).any(axis=(2, 3))
    flat = ink.reshape(-1)
    print(part, "filled cells", int(flat.sum()), "last", int(np.nonzero(flat)[0].max()), "first empty", int(np.argmin(flat)))

chs, jpn = Archive("CHS"), Archive("JPN")
rows = []
for i in used_ids(chs.idx):
    c, j = chs.idx[i][1], jpn.idx[i][1]
    rows.append((i, c, j))
# non-image entries whose sizes differ between languages
for i, c, j in rows:
    if c != j and c < 2_000_000:
        head = chs.read(i)[:4]
        if head not in (b"GT1G", b"XL\x13\x00"):
            print(f"{i:5d} CHS {c:9d} JPN {j:9d} ratio {c/j:.3f} head {head.hex()}")


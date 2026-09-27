"""Locate the boot legal-notice image: base-archive G1T textures that are mostly black with sparse white
and some pure-red pixels. Prints candidates only (no sheets)."""
import numpy as np
from pc_idx import Archive, used_ids
from g1t_pc import parse, decode

for part in ("000", "001", "002", "003"):
    a = Archive(part)
    n = 0
    for e in used_ids(a.idx):
        if a.idx[e][1] < 256 * 1024:
            continue
        try:
            d = a.read(e)
        except Exception:
            continue
        if d[:4] != b"GT1G":
            continue
        try:
            g = parse(d)
        except Exception:
            continue
        for t in g["tex"]:
            if t["w"] < 512:
                continue
            try:
                im = decode(d, t).convert("RGB")
            except Exception:
                continue
            n += 1
            s = np.asarray(im.resize((256, 256 * t["h"] // t["w"] or 1))).astype(int)
            lum = s.mean(axis=2)
            dark = (lum < 20).mean()
            white = (lum > 200).mean()
            red = ((s[..., 0] > 180) & (s[..., 1] < 60) & (s[..., 2] < 60)).mean()
            if dark > 0.75 and 0.005 < white < 0.2 and red > 0.0005:
                print(f"CANDIDATE {part}:{e} t{t['i']} {t['w']}x{t['h']} fmt {t['fmt']:#x} dark {dark:.2f} white {white:.3f} red {red:.4f}", flush=True)
    print(part, "textures checked", n, flush=True)

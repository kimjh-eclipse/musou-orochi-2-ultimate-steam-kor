"""Decode the language font atlas (G1T entry 38, BC3 4096x8192) and measure its cell grid."""
from pathlib import Path
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parents[1] / "extract" / "probe"
W, H, START = 4096, 8192, 0x38


def decode(part):
    d = (P / f"{part}_00038.bin").read_bytes()
    return Image.frombytes("RGBA", (W, H), d[START:START + W * H], "bcn", 3).getchannel("A")


if __name__ == "__main__":
    for part in ("CHS", "JPN"):
        a = decode(part)
        a.save(P / f"{part}_font_alpha.png")
        arr = np.asarray(a)
        col = (arr > 40).sum(axis=0)
        row = (arr > 40).sum(axis=1)
        # find periodic empty gaps: autocorrelation peak of column profile
        def period(v, lo=16, hi=128):
            v = v - v.mean()
            best = max(range(lo, hi), key=lambda p: np.dot(v[:-p], v[p:]) / (len(v) - p))
            return best
        pc, pr = period(col), period(row)
        print(part, "column period", pc, "row period", pr)
        # used area
        ys = np.nonzero(row)[0]
        print("  rows with ink:", ys.min(), ys.max(), " cols:", np.nonzero(col)[0].min(), np.nonzero(col)[0].max())
        # count non-empty cells assuming the measured period
        cols, rows = W // pc, H // pr
        filled = 0
        last = -1
        for r in range(rows):
            for c in range(cols):
                cell = arr[r * pr:(r + 1) * pr, c * pc:(c + 1) * pc]
                if (cell > 40).any():
                    filled += 1
                    last = r * cols + c
        print(f"  grid {cols}x{rows} = {cols*rows}, filled {filled}, last filled index {last}")
        a.crop((0, 8192 - 1024, 2048, 8192)).save(P / f"{part}_font_bottom.png")

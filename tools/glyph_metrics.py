"""Measure CHS hanzi glyph ink boxes inside 48x48 cells, and check for PUA left in Korean strings."""
import json, struct
from pathlib import Path
import numpy as np
from font_grid import decode

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
codes = struct.unpack_from("<9888H", EXE.read_bytes(), 0xB936EE)[1:-1]
arr = np.asarray(decode("CHS"))
boxes = []
for k, c in enumerate(codes):
    if not 0xB0A1 <= c <= 0xF7FE:
        continue
    cell = arr[(k // 85) * 48:(k // 85 + 1) * 48, (k % 85) * 48:(k % 85 + 1) * 48]
    ys, xs = np.nonzero(cell > 64)
    if len(ys):
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
b = np.array(boxes)
print("hanzi cells", len(b))
for name, col in zip(("left", "top", "right", "bottom"), b.T):
    print(f"  {name}: median {np.median(col):.0f}  p5 {np.percentile(col,5):.0f}  p95 {np.percentile(col,95):.0f}")
# typical alpha profile: max value and edge softness
print("  alpha max", arr.max(), "fraction of partial alpha in ink", float(((arr > 0) & (arr < 255)).sum() / max(1, (arr > 0).sum())))

rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
pua = [(r["entry"], r["path"], r["ko"][:30]) for r in rows if r["ko"] and any(0xE000 <= ord(c) <= 0xF8FF for c in r["ko"])]
print("Korean strings containing PUA:", len(pua), pua[:8])

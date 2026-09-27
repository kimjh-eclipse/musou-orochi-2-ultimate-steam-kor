"""compare_images.py <old build> <new build> : replaced image textures per entry; exits 1 if any texture that the
old build replaced is missing from the new one (guards against a spec generator overwriting another's work)."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def texs(ver):
    rep = json.loads((ROOT / "build" / ver / "build_report.json").read_text(encoding="utf-8"))
    return {(x["entry"], x["tex"]) for x in rep["images"]}


old, new = texs(sys.argv[1]), texs(sys.argv[2])
lost, gained = sorted(old - new), sorted(new - old)
print(f"{sys.argv[1]}: {len(old)} textures, {sys.argv[2]}: {len(new)}; lost {len(lost)}, gained {len(gained)}")
if gained:
    print("  gained:", gained[:20])
if lost:
    print("  LOST:", lost[:40])
    sys.exit(1)

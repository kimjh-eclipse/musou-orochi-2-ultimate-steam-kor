"""Read-only inventory of the Steam install: relative path, size, SHA-256."""
import hashlib, json, os, sys, time
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate")
OUT = Path(__file__).resolve().parents[1] / "inventory"
OUT.mkdir(exist_ok=True)

rows = []
for p in sorted(GAME.rglob("*")):
    if not p.is_file():
        continue
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
    rel = p.relative_to(GAME).as_posix()
    rows.append({"path": rel, "size": p.stat().st_size, "sha256": h.hexdigest().upper(),
                 "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))})
    print(rel, rows[-1]["size"], rows[-1]["sha256"][:16], flush=True)

acf = Path(r"C:\Program Files (x86)\Steam\steamapps\appmanifest_1879330.acf").read_text(encoding="utf-8")
meta = {"app_id": 1879330, "game_root": str(GAME), "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "buildid": next((l.split('"')[3] for l in acf.splitlines() if '"buildid"' in l), None),
        "language": next((l.split('"')[3] for l in acf.splitlines() if '"language"' in l), None),
        "files": rows}
(OUT / "pc_inventory.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("DONE", len(rows))

"""Install a build into the Steam game folder (CHS slot), keeping a verified backup of the originals.

  py install.py <version>      install build/<version>
  py install.py --restore      put the original CHS files back
Refuses while WO3U.exe runs, if the current game files are neither original nor a known build,
or if the backup does not match the inventory hashes.
"""
import json, shutil, subprocess, sys
from pathlib import Path
from pack_lang import sha256

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate")
BACKUP = ROOT / "backup" / "original"
FILES = ("LINKIDX_CHS.BIN", "LINKFILE_CHS.BIN")
inv = {r["path"]: r for r in json.loads((ROOT / "inventory/pc_inventory.json").read_text(encoding="utf-8"))["files"]}


def running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WO3U.exe"], capture_output=True, text=True).stdout
    return "WO3U.exe" in out


def known_builds():
    k = {}
    for rep in (ROOT / "build").glob("*/build_report.json"):
        r = json.loads(rep.read_text(encoding="utf-8"))
        for n, v in r["files"].items():
            k.setdefault(n, {})[v["sha256"]] = r["version"]
    return k


def ensure_backup():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for n in FILES:
        b = BACKUP / n
        if b.exists() and sha256(b) == inv[n]["sha256"]:
            continue
        cur = sha256(GAME / n)
        if cur != inv[n]["sha256"]:
            raise SystemExit(f"{n}: no valid backup and game file is not original ({cur[:16]})")
        shutil.copy2(GAME / n, b)
        if sha256(b) != inv[n]["sha256"]:
            raise SystemExit(f"backup of {n} failed verification")
        print("backed up", n)


def put(src_dir, label):
    for n in FILES:
        tmp = GAME / (n + ".tmp_ko")
        shutil.copyfile(src_dir / n, tmp)
        if sha256(tmp) != sha256(src_dir / n):
            tmp.unlink()
            raise SystemExit(f"copy of {n} failed verification")
        tmp.replace(GAME / n)
    for n in FILES:
        print(label, n, sha256(GAME / n)[:16])


def main():
    if running():
        raise SystemExit("WO3U.exe is running; close the game first")
    kb = known_builds()
    for n in FILES:
        cur = sha256(GAME / n)
        if cur != inv[n]["sha256"] and cur not in kb.get(n, {}):
            raise SystemExit(f"{n}: unknown current state {cur[:16]}; refusing")
    ensure_backup()
    if sys.argv[1] == "--restore":
        put(BACKUP, "restored")
        ok = all(sha256(GAME / n) == inv[n]["sha256"] for n in FILES)
        print("original restored" if ok else "RESTORE MISMATCH")
        return
    bdir = ROOT / "build" / sys.argv[1]
    put(bdir, "installed")
    rep = json.loads((bdir / "build_report.json").read_text(encoding="utf-8"))
    ok = all(sha256(GAME / n) == rep["files"][n]["sha256"] for n in FILES)
    print("install verified" if ok else "INSTALL MISMATCH")


if __name__ == "__main__":
    main()

"""Korean for the CHS message tables inside WO3U.exe (in place, same start offsets).

check : exe_patch.py check           -> fit report (bytes incl. NUL <= slot), ESC/format tokens vs JP
build : exe_patch.py build <out.exe> -> patched copy of the ORIGINAL exe (backup/original/WO3U.exe)
Unused slot bytes are zero-filled. The exe on disk has an encrypted .text section; only these data bytes change.
"""
import collections, json, re, shutil, sys
from pathlib import Path
from ko_encode import encode

ROOT = Path(__file__).resolve().parents[1]
GAME_EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
ORIG = ROOT / "backup/original/WO3U.exe"
ESC = re.compile(r"⟨E⟩(?:C\d|R)")
FMT = re.compile(r"%\d*[sdw]")


def rows():
    q = {json.loads(l)["n"]: json.loads(l) for l in (ROOT / "translation_memory/exe_queue.jsonl").open(encoding="utf-8")}
    ko = {json.loads(l)["n"]: json.loads(l)["ko"] for l in (ROOT / "translation_memory/exe_ko.jsonl").open(encoding="utf-8") if l.strip()}
    return q, ko


def check():
    q, ko = rows()
    errs = []
    for n, r in sorted(q.items()):
        k = ko.get(n)
        if k is None:
            errs.append((n, "missing")); continue
        b = encode(k.replace("⟨E⟩", "\x1b"))
        need = len(b) + 1
        if ESC.findall(r["jp"]) != ESC.findall(k):
            errs.append((n, "esc", ESC.findall(r["jp"]), ESC.findall(k)))
        if collections.Counter(FMT.findall(r["jp"])) != collections.Counter(FMT.findall(k)):
            errs.append((n, "fmt"))
        if r["jp"][:2].isdigit() and not k.startswith(r["jp"][:2]):
            errs.append((n, "code"))
        print(f"{n:2} {need:3}/{r['slot']:3} {'OK ' if need <= r['slot'] else 'OVER'} {k[:30]!r}")
        if need > r["slot"]:
            errs.append((n, "over", need - r["slot"]))
    print("errors", errs)
    return not errs


def build(out):
    q, ko = rows()
    d = bytearray(ORIG.read_bytes())
    for n, r in q.items():
        b = encode(ko[n].replace("⟨E⟩", "\x1b"))
        assert len(b) + 1 <= r["slot"]
        assert bytes(d[r["off"]:r["off"] + r["chs_len"]]).decode("gbk") == r["chs"].replace("⟨E⟩", "\x1b")
        d[r["off"]:r["off"] + r["slot"]] = b + b"\0" * (r["slot"] - len(b))
    Path(out).write_bytes(bytes(d))
    print("wrote", out, len(d))


if __name__ == "__main__":
    if not ORIG.exists():
        ORIG.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME_EXE, ORIG)
        print("saved original exe ->", ORIG)
    if sys.argv[1] == "check":
        sys.exit(0 if check() else 1)
    if sys.argv[1] == "build" and check():
        build(sys.argv[2])

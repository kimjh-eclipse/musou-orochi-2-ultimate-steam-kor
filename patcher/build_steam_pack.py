"""Build the Steam patch pack: original CHS part + finished build -> WO3U_Steam_KR.pack

The finished LINKFILE_CHS.BIN is a re-layout of the original (entries in id order, 0x100 aligned), so the
patcher reconstructs it instead of writing ranges in place:

    for every used id in target-offset order:
        stored bytes = pack blob if the id is in the pack, else the original stored bytes of that id
        zero padding up to the target offset, blob, and zero padding up to the target file size

Pack layout (little endian):
    "WO3USTM1"  u32 format(1)  u16 len + UTF-8 version
    2 x file record: u16 len + name, u64 source size, 32B source sha256, u64 target size, 32B target sha256
    u32 len + target LINKIDX_CHS.BIN bytes
    u32 blob count, then per blob: u32 id, u64 length, bytes     (ids ascending)

Only entries whose stored bytes differ from the original are included; unchanged entries come from the
user's own game files.
usage: build_steam_pack.py <version> <build dir> [original dir]
"""
import hashlib, json, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAGIC, FORMAT = b"WO3USTM1", 2
DLL = HERE / "dll/out/mode3/dinput8.dll"
DLL_TABLE = HERE / "dll/strings_table.h"
COMMON003 = HERE / "out/LINKFILE_003.patch"
NAMES = ("LINKIDX_CHS.BIN", "LINKFILE_CHS.BIN")


def read_idx(b):
    return [struct.unpack_from("<QQQQ", b, i * 32) for i in range(len(b) // 32)]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(1 << 24):
            h.update(c)
    return h.digest()


def used(idx):
    return [i for i, r in enumerate(idx) if r[2]]


def reconstruct(base_bin, base_idx, target_idx, blobs, target_size, out_path):
    """Reference implementation of the patcher's rebuild; returns sha256 of the written file."""
    h = hashlib.sha256()
    pos = 0
    with open(base_bin, "rb") as src, open(out_path, "wb") as dst:
        for i in sorted(used(target_idx), key=lambda i: target_idx[i][0]):
            off, _, st, _ = target_idx[i]
            if off < pos:
                raise ValueError(f"overlap at id {i}")
            pad = b"\0" * (off - pos)
            if i in blobs:
                data = blobs[i]
            else:
                bo, _, bst, _ = base_idx[i]
                src.seek(bo)
                data = src.read(bst)
            if len(data) != st:
                raise ValueError(f"size mismatch id {i}")
            for c in (pad, data):
                dst.write(c)
                h.update(c)
            pos = off + st
        tail = b"\0" * (target_size - pos)
        dst.write(tail)
        h.update(tail)
    return h.digest()


def main():
    version, build = sys.argv[1], Path(sys.argv[2])
    orig = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "backup/original"
    oi_b, ti_b = (orig / NAMES[0]).read_bytes(), (build / NAMES[0]).read_bytes()
    oi, ti = read_idx(oi_b), read_idx(ti_b)
    assert len(oi) == len(ti)
    blobs = {}
    with open(orig / NAMES[1], "rb") as fo, open(build / NAMES[1], "rb") as fn:
        for i in used(ti):
            o, n = oi[i], ti[i]
            fn.seek(n[0])
            new = fn.read(n[2])
            if o[2] == n[2] and o[1:] == n[1:]:
                fo.seek(o[0])
                if fo.read(o[2]) == new:
                    continue
            blobs[i] = new
    # the dinput8 proxy must carry the string table generated for this very build (font index CRC)
    import re, zlib
    crc = int(re.search(r"KR_IDX_CRC32 0x([0-9a-f]+)u", DLL_TABLE.read_text()).group(1), 16)
    if crc != zlib.crc32(ti_b):
        sys.exit(f"dll table is for idx crc {crc:08x}, build idx is {zlib.crc32(ti_b):08x}: run gen_dll_patch.py + build_dll.cmd")
    dll = DLL.read_bytes()
    if b"WO3U_KR dinput8 proxy, mode " not in dll or DLL.stat().st_mtime < DLL_TABLE.stat().st_mtime:
        sys.exit("dinput8.dll is not the mode 3 build of the current table")
    files = []
    for name in NAMES:
        files.append((name, (orig / name).stat().st_size, sha(orig / name), (build / name).stat().st_size, sha(build / name)))
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    pack = out / "WO3U_Steam_KR.pack"
    with open(pack, "wb") as f:
        v = version.encode()
        f.write(MAGIC + struct.pack("<IH", FORMAT, len(v)) + v)
        for name, ssz, ssh, tsz, tsh in files:
            nb = name.encode()
            f.write(struct.pack("<H", len(nb)) + nb + struct.pack("<Q", ssz) + ssh + struct.pack("<Q", tsz) + tsh)
        f.write(struct.pack("<I", len(ti_b)) + ti_b)
        extras = [(b"dinput8.dll", dll)]
        if COMMON003.exists():  # DLC costume source texts in the common part (tools/gen_common003.py)
            extras.append((b"LINKFILE_003.patch", COMMON003.read_bytes()))
        f.write(struct.pack("<I", len(extras)))
        for nb, data in extras:
            f.write(struct.pack("<H", len(nb)) + nb + hashlib.sha256(data).digest() + struct.pack("<I", len(data)) + data)
        f.write(struct.pack("<I", len(blobs)))
        for i in sorted(blobs):
            f.write(struct.pack("<IQ", i, len(blobs[i])) + blobs[i])
    # independent check: rebuild from the original with the pack contents and compare hashes
    tmp = out / "_reconstructed_LINKFILE_CHS.BIN"
    got = reconstruct(orig / NAMES[1], oi, ti, blobs, files[1][3], tmp)
    ok = got == files[1][4]
    tmp.unlink()
    manifest = {"version": version, "entries": len(blobs), "blob_bytes": sum(map(len, blobs.values())),
                "pack_size": pack.stat().st_size, "pack_sha256": sha(pack).hex().upper(),
                "files": [{"name": n, "source_size": a, "source_sha256": b.hex().upper(), "target_size": c,
                           "target_sha256": d.hex().upper()} for n, a, b, c, d in files],
                "dll": {"name": "dinput8.dll", "size": len(dll), "sha256": hashlib.sha256(dll).hexdigest().upper(),
                        "table_idx_crc32": f"{crc:08x}"},
                "common003": {"size": COMMON003.stat().st_size, "sha256": sha(COMMON003).hex().upper()} if COMMON003.exists() else None,
                "reconstruct_ok": ok}
    (out / "WO3U_Steam_KR.manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=1))
    if not ok:
        sys.exit("reconstruction hash mismatch")


if __name__ == "__main__":
    main()

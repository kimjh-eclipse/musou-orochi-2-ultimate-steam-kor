"""Write a language part (LINKIDX_<part>.BIN + LINKFILE_<part>.BIN) with some entries replaced.

replacements: {entry_id: decompressed bytes}. Replaced entries are compressed like the original entry
(same chunk size) or stored raw if the original was raw. Layout matches the original: ids in order,
offsets aligned to 0x100, zero padding between entries.
"""
import hashlib, struct
from pathlib import Path
from pc_idx import Archive, compress, used_ids, decompress

ALIGN = 0x100


def write_part(part, replacements, out_dir: Path):
    a = Archive(part)
    out_dir.mkdir(parents=True, exist_ok=True)
    idx = list(a.idx)
    ids = set(used_ids(idx))
    fbin = out_dir / f"LINKFILE_{part}.BIN"
    info = {}
    with fbin.open("wb") as f:
        pos = 0
        for i in sorted(ids, key=lambda i: idx[i][0]):
            off, un, st, c = idx[i]
            if i in replacements:
                data = replacements[i]
                if c:
                    blob = compress(data, a.chunk_size(i))
                    assert decompress(blob, len(data))[0] == data
                else:
                    blob = data
                new = (pos, len(data), len(blob), c)
                info[i] = {"old_stored": st, "new_stored": len(blob), "unpacked": len(data)}
            else:
                blob = a.raw(i)
                new = (pos, un, st, c)
            f.write(blob)
            end = pos + len(blob)
            padded = (end + ALIGN - 1) // ALIGN * ALIGN
            f.write(b"\0" * (padded - end))
            idx[i] = new
            pos = padded
    orig_len = (a.f.seek(0, 2))
    raw_idx = b"".join(struct.pack("<QQQQ", *r) for r in idx)
    (out_dir / f"LINKIDX_{part}.BIN").write_bytes(raw_idx)
    return {"part": part, "bin_size": fbin.stat().st_size, "orig_bin_size": orig_len, "replaced": info}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest().upper()


if __name__ == "__main__":
    import json, sys
    root = Path(__file__).resolve().parents[1]
    inv = {r["path"]: r for r in json.loads((root / "inventory/pc_inventory.json").read_text(encoding="utf-8"))["files"]}
    out = root / "build" / "_identity"
    rep = write_part("CHS", {}, out)
    for name in ("LINKIDX_CHS.BIN", "LINKFILE_CHS.BIN"):
        got = sha256(out / name)
        print(name, "identical to original" if got == inv[name]["sha256"] else f"DIFFERS {got}")
    print(rep["bin_size"], rep["orig_bin_size"])

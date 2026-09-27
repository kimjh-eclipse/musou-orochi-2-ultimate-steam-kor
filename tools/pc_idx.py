"""Steam WO3U DE LINKIDX_*.BIN / LINKFILE_*.BIN reader and entry codec.

IDX: 36,200 records of <QQQQ = (offset, unpacked_size, stored_size, compressed).
All eight IDX files share one id space; each file fills only the ids it stores.
The four language files hold the same 2,022 ids.

Compressed entry: <III (chunk_size, block_count, unpacked_size), <I sizes[block_count],
header padded to 0x80; each block = <I zlib_len + zlib stream, padded to 0x80.
"""
import struct, zlib
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate")
PARTS = ["000", "001", "002", "003", "CHS", "CHT", "ENG", "JPN"]
LANGS = ["CHS", "CHT", "ENG", "JPN"]


def align(v, a=0x80):
    return (v + a - 1) & ~(a - 1)


def read_idx(part, game=GAME):
    data = (game / f"LINKIDX_{part}.BIN").read_bytes()
    return [struct.unpack_from("<QQQQ", data, i * 32) for i in range(len(data) // 32)]


def used_ids(idx):
    return [i for i, r in enumerate(idx) if r[1] or r[2]]


def decompress(blob, expected=None):
    chunk, count, total = struct.unpack_from("<III", blob)
    sizes = struct.unpack_from(f"<{count}I", blob, 12)
    cur = align(12 + 4 * count)
    out = bytearray()
    for n, rec in enumerate(sizes):
        ln = struct.unpack_from("<I", blob, cur)[0]
        if ln + 4 > rec:
            raise ValueError(f"block {n}: len {ln} > record {rec}")
        out += zlib.decompress(blob[cur + 4:cur + 4 + ln])
        cur = align(cur + rec)
    if len(out) != total or (expected is not None and total != expected):
        raise ValueError(f"size {len(out)} / header {total} / idx {expected}")
    return bytes(out), chunk


def compress(data, chunk=0x10000, level=9):
    recs = []
    for o in range(0, len(data), chunk):
        z = zlib.compress(data[o:o + chunk], level)
        recs.append(struct.pack("<I", len(z)) + z)
    out = bytearray(struct.pack("<III", chunk, len(recs), len(data)))
    out += struct.pack(f"<{len(recs)}I", *[len(r) for r in recs])
    out += b"\0" * (align(len(out)) - len(out))
    for r in recs:
        out += r
        out += b"\0" * (align(len(out)) - len(out))
    return bytes(out)


BACKUP = Path(__file__).resolve().parents[1] / "backup" / "original"


def source_dir(part):
    """Pristine source for a part: the verified backup once a patch is installed, else the game folder."""
    if (BACKUP / f"LINKIDX_{part}.BIN").exists() and (BACKUP / f"LINKFILE_{part}.BIN").exists():
        return BACKUP
    return GAME


class Archive:
    def __init__(self, part, game=None):
        game = source_dir(part) if game is None else game
        self.part = part
        self.idx = read_idx(part, game)
        self.f = open(game / f"LINKFILE_{part}.BIN", "rb")

    def raw(self, i):
        off, a, b, c = self.idx[i]
        self.f.seek(off)
        return self.f.read(b)

    def read(self, i):
        off, a, b, c = self.idx[i]
        blob = self.raw(i)
        return decompress(blob, a)[0] if c else blob

    def chunk_size(self, i):
        return struct.unpack_from("<I", self.raw(i)[:4])[0] if self.idx[i][3] else None

"""DLC costume source texts (gallery '의상 출전', issues #10/#11) live in the common part 003, not in the CHS slot.

Each DLC costume has a small compressed entry in LINKFILE_003.BIN with four language records (JP, ENG, CHT, CHS);
with the game language set to Simplified Chinese the CHS record is shown, so it appeared as broken glyphs.
This tool writes the Korean text into the CHS record of every such entry (same uncompressed size: the string is
written into its original bytes + padding), recompresses it and keeps it only if it fits the original stored size.

Output: <out> (default patcher/out/LINKFILE_003.patch), consumed by build_steam_pack.py as a pack extra:
    "WO3UC003" u32 count, then per entry: u32 id, u64 offset, u32 stored size,
    32B sha256 of the original stored bytes, 32B sha256 of the new stored bytes (padded to stored size), new bytes
usage: gen_common003.py [out]
"""
import hashlib, re, struct, sys, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from ko_encode import can_encode, encode
from pc_idx import Archive, GAME, align, used_ids

KO = {
    "『真・三國無双６』": "『진・삼국무쌍 6』",
    "『無双OROCHI２』": "『무쌍 오로치 2』",
    "『真・三國無双 MULTI RAID 2』": "『진・삼국무쌍 MULTI RAID 2』",
    "『無双OROCHI Z』": "『무쌍 오로치 Z』",
    "『真・三國無双２』": "『진・삼국무쌍 2』",
    "『真・三國無双３』": "『진・삼국무쌍 3』",
    "『無双OROCHI２ Ultimate』": "『무쌍오로치2 Ultimate』",   # the full Korean title does not fit 24 bytes
    "『真・三國無双６ 猛将伝』": "『진・삼국무쌍 6 맹장전』",
    "『三國無双』": "『삼국무쌍』",
    "『初回限定特典』": "『초회 특전』",                  # two of these entries have only 384 stored bytes
    "『討鬼伝コラボ衣装』": "『토귀전 콜라보 의상』",
    "『NINJA GAIDEN Σ２』": "『NINJA GAIDEN Σ2』",
    "『DEAD OR ALIVE 5 Ultimate』": "『DEAD OR ALIVE 5 Ultimate』",
    "『NINJA GAIDEN 3: Razor's Edge』": "『NINJA GAIDEN 3: Razor's Edge』",
    "『DEAD OR ALIVE 5』": "『DEAD OR ALIVE 5』",
    "「アーランドのアトリエ」シリーズ": "「아란드의 아틀리에」 시리즈",
}
REC = re.compile(rb"(DLC_\d+_\d+)\x00+([^\x00]+)(\x00+)")
ZERO = bytes(1)


def compress_tight(data, chunk):
    """pc_idx.compress layout without the alignment padding after the last record (the slot is zero-padded anyway)."""
    recs = []
    for o in range(0, len(data), chunk):
        z = zlib.compress(data[o:o + chunk], 9)
        recs.append(struct.pack("<I", len(z)) + z)
    out = bytearray(struct.pack("<III", chunk, len(recs), len(data)))
    out += struct.pack(f"<{len(recs)}I", *[len(r) for r in recs])
    out += ZERO * (align(len(out)) - len(out))
    for k, r in enumerate(recs):
        out += r
        if k + 1 < len(recs):
            out += ZERO * (align(len(out)) - len(out))
    return bytes(out)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "patcher/out/LINKFILE_003.patch"
    arc = Archive("003", GAME)
    records, skipped = [], []
    for e in used_ids(arc.idx):
        off, size, stored, comp = arc.idx[e]
        if size > 4096 or not comp:
            continue
        data = arc.read(e)
        if b"XL\x13\x00" not in data or b"DLC_" not in data:
            continue
        recs = list(REC.finditer(data))
        if len(recs) != 4:
            sys.exit(f"entry {e}: {len(recs)} language records")
        jp = recs[0].group(2).decode("cp932")
        ko = KO[jp]
        assert can_encode(ko), ko
        chs = recs[3]
        new = encode(ko)
        room = len(chs.group(2)) + len(chs.group(3)) - 1           # keep at least one terminating NUL
        if len(new) > room:
            sys.exit(f"entry {e}: {ko} needs {len(new)} bytes, room {room}")
        buf = bytearray(data)
        buf[chs.start(2):chs.end(3)] = new + ZERO * (room + 1 - len(new))
        assert len(buf) == len(data)
        orig = arc.raw(e)
        chunk = struct.unpack_from("<I", orig)[0]
        blob = compress_tight(bytes(buf), chunk)
        if len(blob) > stored:
            skipped.append((e, jp, len(blob), stored))
            continue
        assert zlib.decompress(blob[align(12 + 4) + 4:]) == bytes(buf) or chunk < len(buf)
        padded = blob + ZERO * (stored - len(blob))
        records.append((e, off, stored, hashlib.sha256(orig).digest(), hashlib.sha256(padded).digest(), padded))
    with open(out, "wb") as f:
        f.write(b"WO3UC003" + struct.pack("<I", len(records)))
        for e, off, stored, oh, nh, data in records:
            f.write(struct.pack("<IQI", e, off, stored) + oh + nh + data)
    print(f"{len(records)} entries -> {out.name} ({out.stat().st_size:,} B); skipped (too big) {len(skipped)}: {skipped[:5]}")
    if skipped:
        sys.exit(1)


if __name__ == "__main__":
    main()

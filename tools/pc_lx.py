"""PC (little-endian) LX string tables: direct 'XL' or a <I count + (<II off,size)[] bundle of them."""
import struct


def sections(data):
    if data[:2] == b"XL":
        return [(0, len(data))]
    if len(data) < 12:
        return []
    n = struct.unpack_from("<I", data)[0]
    if not 1 <= n <= 256 or 4 + n * 8 > len(data):
        return []
    desc = [struct.unpack_from("<II", data, 4 + i * 8) for i in range(n)]
    if not all(4 + n * 8 <= o < len(data) and data[o:o + 2] == b"XL" for o, s in desc):
        return []
    return [(o, o + s) for o, s in desc]


def records(data):
    """Yield (section, index, pointer_offset, string_offset, raw_bytes)."""
    for sec, (base, end) in enumerate(sections(data)):
        ver = struct.unpack_from("<H", data, base + 2)[0]
        count, width = struct.unpack_from("<HH", data, base + 8)
        table = base + struct.unpack_from("<I", data, base + 12)[0]
        if ver not in (0x13, 0x14) or width < 4 or table + count * width > end:
            raise ValueError(f"LX layout sec {sec}: ver {ver:#x} count {count} width {width}")
        for i in range(count):
            p = table + i * width + width - 4
            rel = struct.unpack_from("<I", data, p)[0]
            if rel == 0xFFFFFFFF:
                continue
            o = table + rel
            if end <= o <= end + 3:
                continue
            nul = data.find(b"\0", o, end)
            if not table + count * width <= o < end or nul < 0:
                raise ValueError(f"pointer sec {sec} rec {i} -> {o:#x}")
            yield sec, i, p, o, data[o:nul]

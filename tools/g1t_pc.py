"""PC (little-endian) G1T texture container: parse, decode, replace texture data.

Header: 'GT1G' '0600' <I file_size <I table_off <I count <I platform <I ? ...
table: <I rel_offset[count] (relative to table_off)
texture: [0]=mip<<4|sys [1]=format [2]=dx|dy<<4 [3..6] [7]=extra flag; if extra: <I extra_size, extra bytes;
         pixel data follows (mip 0 first).
"""
import struct
from PIL import Image

FORMATS = {  # format: (bytes per 4x4 block or per pixel, kind)
    0x01: ("rgba8", 4), 0x02: ("bgra8", 4),
    0x59: ("bc1", 8), 0x5A: ("bc2", 16), 0x5B: ("bc3", 16),
    0x5C: ("bc4", 8), 0x5D: ("bc5", 16), 0x5E: ("bc6", 16), 0x5F: ("bc7", 16),
    0x06: ("bc1", 8), 0x07: ("bc2", 16), 0x08: ("bc3", 16),
}


def parse(d):
    if d[:4] != b"GT1G":
        raise ValueError("not GT1G")
    size, table, count, platform = struct.unpack_from("<IIII", d, 8)
    offs = struct.unpack_from(f"<{count}I", d, table)
    tex = []
    for i, rel in enumerate(offs):
        p = table + rel
        mip, fmt, dxdy = d[p], d[p + 1], d[p + 2]
        w, h = 1 << (dxdy & 15), 1 << (dxdy >> 4)
        extra = d[p + 7]
        esz = struct.unpack_from("<I", d, p + 8)[0] if extra else 0
        if extra and esz >= 0x14:
            w2, h2 = struct.unpack_from("<II", d, p + 8 + 0x0C)
            if w2 and h2:
                w, h = w2, h2
        data = p + 8 + esz
        end = table + offs[i + 1] if i + 1 < count else len(d)
        tex.append({"i": i, "hdr": p, "fmt": fmt, "w": w, "h": h, "mips": mip >> 4, "data": data, "end": end})
    return {"size": size, "table": table, "count": count, "platform": platform, "tex": tex}


def level0_size(t):
    kind, b = FORMATS.get(t["fmt"], (None, 0))
    if kind is None:
        return None
    if kind.startswith("bc"):
        return max(1, (t["w"] + 3) // 4) * max(1, (t["h"] + 3) // 4) * b
    return t["w"] * t["h"] * b


def encode(img, t):
    """Encode an RGBA image for texture t (same size/format) -> level-0 bytes."""
    import io
    kind, b = FORMATS.get(t["fmt"], (None, 0))
    img = img.convert("RGBA")
    assert img.size == (t["w"], t["h"]), (img.size, t["w"], t["h"])
    if kind == "rgba8":
        return img.tobytes("raw", "RGBA")
    if kind == "bgra8":
        return img.tobytes("raw", "BGRA")
    if kind in ("bc1", "bc3"):
        buf = io.BytesIO()
        img.save(buf, "DDS", pixel_format="DXT1" if kind == "bc1" else "DXT5")
        raw = buf.getvalue()[128:]
        assert len(raw) == level0_size(t), (len(raw), level0_size(t))
        return raw
    raise ValueError(f"cannot encode format {t['fmt']:#x}")


def replace(d, t, img):
    """Return new G1T bytes with texture t's level-0 pixels replaced (container layout unchanged)."""
    raw = encode(img, t)
    out = bytearray(d)
    out[t["data"]:t["data"] + len(raw)] = raw
    return bytes(out)


def decode(d, t):
    kind, b = FORMATS.get(t["fmt"], (None, 0))
    n = level0_size(t)
    if kind is None or n is None:
        raise ValueError(f"format {t['fmt']:#x}")
    raw = d[t["data"]:t["data"] + n]
    w, h = t["w"], t["h"]
    if kind == "rgba8":
        return Image.frombytes("RGBA", (w, h), raw, "raw", "RGBA")
    if kind == "bgra8":
        return Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA")
    num = {"bc1": 1, "bc2": 2, "bc3": 3, "bc4": 4, "bc5": 5, "bc6": 6, "bc7": 7}[kind]
    mode = "RGBA" if num in (1, 2, 3, 7) else ("L" if num == 4 else "RGB")
    args = (num,) if num != 6 else (num, 0)
    return Image.frombytes(mode, (w, h), raw, "bcn", *args).convert("RGBA")

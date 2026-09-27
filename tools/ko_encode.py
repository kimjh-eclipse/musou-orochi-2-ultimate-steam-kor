"""Unicode -> CHS-slot bytes.

ASCII passes through (control codes \x1b.., %s, newlines). Characters in ko_charset.json use their donor
GBK code. Everything else must be a kept (non-donor) entry of the CHS code table, encoded as GBK.
Special: U+E032 (PS3/JP user-defined registered mark) -> GBK AAA1, the CHS code for the same glyph.
"""
import json, struct
from pathlib import Path
from ko_charset import table_codes, is_hanzi_code

ROOT = Path(__file__).resolve().parents[1]
_charset = json.loads((ROOT / "mapping/ko_charset.json").read_text(encoding="utf-8"))["chars"]
DONOR = {ch: bytes.fromhex(h) for ch, h in _charset.items()}
_codes = table_codes()
KEPT = {}
for c in _codes:
    if is_hanzi_code(c):
        continue
    b = struct.pack(">H", c)
    try:
        KEPT[b.decode("gbk")] = b
    except UnicodeDecodeError:
        pass
SPECIAL = {"": b"\xaa\xa1"}


class EncodeError(ValueError):
    pass


def encode(s):
    out = bytearray()
    for ch in s:
        o = ord(ch)
        if o < 0x80:
            out.append(o)
        elif ch in DONOR:
            out += DONOR[ch]
        elif ch in SPECIAL:
            out += SPECIAL[ch]
        elif ch in KEPT:
            out += KEPT[ch]
        else:
            raise EncodeError(f"no glyph for {ch!r} U+{o:04X}")
    return bytes(out)


def can_encode(s):
    try:
        encode(s)
        return True
    except EncodeError:
        return False


def decode(b):
    """Inverse for verification."""
    rev = {v: k for k, v in DONOR.items()}
    rev.update({v: k for k, v in KEPT.items()})
    rev.update({v: k for k, v in SPECIAL.items()})
    out, i = [], 0
    while i < len(b):
        if b[i] < 0x80:
            out.append(chr(b[i])); i += 1
        else:
            out.append(rev.get(b[i:i + 2], "�")); i += 2
    return "".join(out)

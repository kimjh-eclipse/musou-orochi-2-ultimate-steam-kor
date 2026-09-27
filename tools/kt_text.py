"""Generic finder for text in KT resources (PS3 big-endian / PC little-endian).

Recognised nodes:
  LX   : 'LX'/'XL' string table (record pointer = last 4 bytes, relative to table start)
  LIST : u32 n, u32 off[n] (relative to section start, off[0] == 4 + 4n), NUL strings
  CONT : u32 n, (u32 off, u32 size)[n] with ascending in-bounds sections -> recurse

walk(data, endian) yields Str(path, kind, pointer_pos, string_pos, raw) with absolute positions.
"""
import struct
from dataclasses import dataclass


@dataclass
class Str:
    path: tuple
    kind: str
    ptr: int
    pos: int
    raw: bytes


def _u32(d, o, e):
    return struct.unpack_from(e + "I", d, o)[0]


def _u16(d, o, e):
    return struct.unpack_from(e + "H", d, o)[0]


def is_lx(d, base, end, e):
    sig = b"LX" if e == ">" else b"XL"
    if end - base < 16 or d[base:base + 2] != sig:
        return False
    ver = _u16(d, base + 2, e)
    count, width = _u16(d, base + 8, e), _u16(d, base + 10, e)
    table = base + _u32(d, base + 12, e)
    return ver in (0x13, 0x14) and width >= 4 and table + count * width <= end


def lx_strings(d, base, end, e, path):
    count, width = _u16(d, base + 8, e), _u16(d, base + 10, e)
    table = base + _u32(d, base + 12, e)
    out = []
    for i in range(count):
        p = table + i * width + width - 4
        rel = _u32(d, p, e)
        if rel == 0xFFFFFFFF:
            continue
        o = table + rel
        if end <= o <= end + 3:
            continue
        nul = d.find(b"\0", o, end)
        if not table + count * width <= o < end or nul < 0:
            return None
        out.append(Str(path + (i,), "LX", p, o, d[o:nul]))
    return out


def list_strings(d, base, end, e, path):
    if end - base < 8:
        return None
    n = _u32(d, base, e)
    if not 1 <= n <= 100000 or base + 4 + 4 * n > end:
        return None
    offs = [_u32(d, base + 4 + 4 * k, e) for k in range(n)]
    if offs[0] != 4 + 4 * n:
        return None
    out = []
    prev = 0
    for k, o in enumerate(offs):
        a = base + o
        if o < prev or not base + 4 + 4 * n <= a < end:
            return None
        nul = d.find(b"\0", a, end)
        if nul < 0:
            return None
        out.append(Str(path + (k,), "LIST", base + 4 + 4 * k, a, d[a:nul]))
        prev = o
    # strings must tile the section: last string ends near section end (allow 4-byte padding)
    last_end = d.find(b"\0", base + offs[-1], end) + 1
    if end - last_end > 4 or any(d[last_end:end]):
        return None
    return out


def cont_sections(d, base, end, e):
    if end - base < 12:
        return None
    n = _u32(d, base, e)
    if not 1 <= n <= 256 or base + 4 + 8 * n > end:
        return None
    secs = []
    cur = base + 4 + 8 * n
    for k in range(n):
        o, s = _u32(d, base + 4 + 8 * k, e), _u32(d, base + 8 + 8 * k, e)
        a = base + o
        if a < cur - 0 or a + s > end:
            return None
        secs.append((a, a + s))
        cur = a + s
    return secs


def walk(d, e, base=0, end=None, path=(), depth=0):
    end = len(d) if end is None else end
    if is_lx(d, base, end, e):
        r = lx_strings(d, base, end, e, path)
        return r or []
    r = list_strings(d, base, end, e, path)
    if r is not None:
        return r
    if depth < 4:
        secs = cont_sections(d, base, end, e)
        if secs:
            out = []
            for k, (a, b) in enumerate(secs):
                out += walk(d, e, a, b, path + (k,), depth + 1)
            return out
    return []


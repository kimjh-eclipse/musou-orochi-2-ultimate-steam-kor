"""Rebuild KT text resources (PC little-endian) with replaced strings.

rebuild(data, repl) -> bytes, where repl maps string path (tuple) -> new raw bytes (without NUL).
Identity rebuild (repl empty) must return the original bytes; test_rebuild.py checks that.

Layout rules (measured on the PC files):
  CONT : sections kept in order; each section starts at the original gap alignment
  LX   : header+table kept; pool = strings in original position order, records that shared
         a string keep sharing; +4 u16 = section size & 0xFFFF
  LIST : offsets rewritten, strings concatenated; trailing zero padding kept per original
"""
import struct
from kt_text import is_lx, list_strings, cont_sections, lx_strings

E = "<"


def _align(v, a):
    return (v + a - 1) // a * a if a > 1 else v


def _tail_pad(orig_len, content_len):
    return orig_len - content_len


def _rebuild_lx(d, base, end, repl, path):
    strs = lx_strings(d, base, end, E, path)
    if not strs or not any(s.path in repl for s in strs):
        return d[base:end]
    sec = bytearray(d[base:end])
    first = min(s.pos for s in strs) - base
    by_pos = {}
    for s in strs:
        by_pos.setdefault(s.pos, []).append(s)
    pool = bytearray()
    table = struct.unpack_from("<I", sec, 12)[0]
    ptr_rel = {}
    # keep any bytes between table end and first string (padding) as-is
    for pos in sorted(by_pos):
        group = by_pos[pos]
        raws = {repl.get(s.path, s.raw) for s in group}
        if len(raws) == 1:
            new = raws.pop()
            rel = first + len(pool) - table
            for s in group:
                ptr_rel[s.ptr - base] = rel
            pool += new + b"\0"
        else:  # records that shared a string now differ: give each its own copy
            for s in group:
                rel = first + len(pool) - table
                ptr_rel[s.ptr - base] = rel
                pool += repl.get(s.path, s.raw) + b"\0"
    orig_pool_end = max(s.pos + len(s.raw) + 1 for s in strs) - base
    trailer = bytes(sec[orig_pool_end:])  # original zero padding after the pool
    pad_to = 4 if (end - base) % 4 == 0 else 1
    out = bytearray(sec[:first]) + pool
    if trailer.strip(b"\0"):
        raise ValueError(f"LX {path}: non-zero data after string pool")
    out += b"\0" * (_align(len(out), pad_to) - len(out)) if pad_to > 1 else trailer[:0]
    if len(out) < len(sec) and not repl:
        out += trailer
    for p, rel in ptr_rel.items():
        struct.pack_into("<I", out, p, rel)
    struct.pack_into("<H", out, 4, len(out) & 0xFFFF)
    return bytes(out)


def _rebuild_list(d, base, end, repl, path):
    strs = list_strings(d, base, end, E, path)
    if not any(s.path in repl for s in strs):
        return d[base:end]
    n = len(strs)
    out = bytearray(struct.pack("<I", n)) + bytearray(4 * n)
    for k, s in enumerate(strs):
        struct.pack_into("<I", out, 4 + 4 * k, len(out))
        out += repl.get(s.path, s.raw) + b"\0"
    pad = 4 if (end - base) % 4 == 0 and (end - base) > (d.find(b"\0", strs[-1].pos, end) + 1 - base) else 1
    if pad > 1:
        out += b"\0" * (_align(len(out), 4) - len(out))
    return bytes(out)


def _rebuild_cont(d, base, end, secs, repl, path, depth):
    n = len(secs)
    head = bytearray(d[base:base + 4 + 8 * n])
    parts = [rebuild(d, repl, a, b, path + (k,), depth + 1) for k, (a, b) in enumerate(secs)]
    if all(p == d[a:b] for p, (a, b) in zip(parts, secs)):
        return d[base:end]
    # alignment of each section start, inferred from the original gap after the previous section
    out = bytearray(head)
    prev_end = base + 4 + 8 * n
    for k, ((a, b), p) in enumerate(zip(secs, parts)):
        gap = a - prev_end
        rel_a = a - base
        al = 1
        for cand in (16, 8, 4, 2):
            if rel_a % cand == 0:
                al = cand
                break
        # only pad when the original needed padding to reach this alignment
        start = _align(len(out), al) if gap > 0 else len(out)
        out += b"\0" * (start - len(out))
        struct.pack_into("<II", out, 4 + 8 * k, start, len(p))
        out += p
        prev_end = b
    tail = end - secs[-1][1]
    out += b"\0" * tail
    return bytes(out)


def rebuild(d, repl, base=0, end=None, path=(), depth=0):
    end = len(d) if end is None else end
    if is_lx(d, base, end, E):
        if lx_strings(d, base, end, E, path):
            return _rebuild_lx(d, base, end, repl, path)
        return d[base:end]
    if list_strings(d, base, end, E, path) is not None:
        return _rebuild_list(d, base, end, repl, path)
    if depth < 4:
        secs = cont_sections(d, base, end, E)
        if secs:
            return _rebuild_cont(d, base, end, secs, repl, path, depth)
    return d[base:end]

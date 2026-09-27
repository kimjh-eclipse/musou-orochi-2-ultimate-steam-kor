"""Minimal BC3 (DXT5) alpha-block encoder / block access for the 4096x8192 font atlas."""
import numpy as np

W, H = 4096, 8192
BPR = W // 4  # blocks per row


def block_offset(bx, by, base=0x38):
    return base + (by * BPR + bx) * 16


def encode_alpha_block(a):
    """a: (16,) uint8 in row-major 4x4 order -> 8 bytes (a0, a1, 48-bit indices)."""
    hi, lo = int(a.max()), int(a.min())
    if hi == lo:
        return bytes([hi, lo]) + b"\0" * 6
    # 8-value mode (a0 > a1)
    pal = np.array([hi, lo] + [((7 - i) * hi + i * lo) // 7 for i in range(1, 7)], dtype=np.int32)
    idx = np.abs(a.astype(np.int32)[:, None] - pal[None, :]).argmin(axis=1)
    bits = 0
    for k, v in enumerate(idx):
        bits |= int(v) << (3 * k)
    return bytes([hi, lo]) + bits.to_bytes(6, "little")


def decode_alpha_block(b):
    a0, a1 = b[0], b[1]
    if a0 > a1:
        pal = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    else:
        pal = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
    bits = int.from_bytes(b[2:8], "little")
    return np.array([pal[(bits >> (3 * k)) & 7] for k in range(16)], dtype=np.uint8)


def write_cell_alpha(buf, cell_x, cell_y, alpha48, base=0x38):
    """Replace the alpha halves of the 12x12 blocks of one 48x48 cell; colour halves untouched."""
    for by in range(12):
        for bx in range(12):
            blk = alpha48[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4].reshape(16)
            o = block_offset(cell_x * 12 + bx, cell_y * 12 + by, base)
            buf[o:o + 8] = encode_alpha_block(blk)

import sys

def dump(path, off=0, n=256):
    with open(path, "rb") as f:
        f.seek(off)
        b = f.read(n)
    for i in range(0, len(b), 16):
        c = b[i:i + 16]
        print(f"{off + i:08X}  {c.hex(' '):<48}  {''.join(chr(x) if 32 <= x < 127 else '.' for x in c)}")

if __name__ == "__main__":
    p = sys.argv[1]
    off = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    n = int(sys.argv[3], 0) if len(sys.argv) > 3 else 256
    dump(p, off, n)

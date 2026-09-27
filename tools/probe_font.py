import struct, sys
from pathlib import Path
from pc_idx import Archive
from hexdump import dump

OUT = Path(__file__).resolve().parents[1] / "extract" / "probe"
OUT.mkdir(parents=True, exist_ok=True)

for part in ("CHS", "JPN"):
    a = Archive(part)
    for i in (33, 34, 37, 38, 43, 44):
        d = a.read(i)
        (OUT / f"{part}_{i:05d}.bin").write_bytes(d)
        print(f"== {part} {i} size {len(d)}")
        tmp = OUT / "_tmp.bin"
        tmp.write_bytes(d[:0x60])
        dump(str(tmp), 0, 0x60)

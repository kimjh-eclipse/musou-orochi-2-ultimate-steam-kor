"""minidump_module.py <dmp> : module name + offset of the exception address."""
import struct, sys
from minidump_info import Dump

d = Dump(sys.argv[1])
size, loc = d.streams[6]
code, flags, rec, addr = struct.unpack_from("<IIQQ", d.d, loc + 8)
for base, sz, name in d.modules():
    if base <= addr < base + sz:
        print(hex(code), name.split("\\")[-1], hex(addr - base))
        break
else:
    print(hex(code), "unknown module", hex(addr))

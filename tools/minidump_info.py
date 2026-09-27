"""minidump_info.py <dmp> : exception, registers, module base, and printable strings near registers / stack.

Minimal MINIDUMP reader (x64): streams ThreadList(3), ModuleList(4), MemoryList(5), Exception(6), Memory64List(9).
"""
import struct, sys

REGS = ["RAX", "RCX", "RDX", "RBX", "RSP", "RBP", "RSI", "RDI", "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15"]


class Dump:
    def __init__(self, path):
        self.d = open(path, "rb").read()
        sig, ver, n, rva = struct.unpack_from("<4sIII", self.d)
        assert sig == b"MDMP"
        self.streams = {}
        for i in range(n):
            t, size, loc = struct.unpack_from("<III", self.d, rva + i * 12)
            self.streams.setdefault(t, (size, loc))
        self.ranges = []
        if 9 in self.streams:
            _, loc = self.streams[9]
            cnt, base_rva = struct.unpack_from("<QQ", self.d, loc)
            off = base_rva
            for i in range(cnt):
                start, size = struct.unpack_from("<QQ", self.d, loc + 16 + i * 16)
                self.ranges.append((start, size, off))
                off += size
        if 5 in self.streams:
            _, loc = self.streams[5]
            cnt = struct.unpack_from("<I", self.d, loc)[0]
            for i in range(cnt):
                start, size, rva2 = struct.unpack_from("<QII", self.d, loc + 4 + i * 16)
                self.ranges.append((start, size, rva2))

    def read(self, addr, n):
        for start, size, off in self.ranges:
            if start <= addr < start + size:
                k = min(n, start + size - addr)
                return self.d[off + addr - start: off + addr - start + k]
        return None

    def modules(self):
        _, loc = self.streams[4]
        cnt = struct.unpack_from("<I", self.d, loc)[0]
        out = []
        for i in range(cnt):
            base, size, _, _, name_rva = struct.unpack_from("<QIIII", self.d, loc + 4 + i * 108)
            ln = struct.unpack_from("<I", self.d, name_rva)[0]
            name = self.d[name_rva + 4:name_rva + 4 + ln].decode("utf-16le")
            out.append((base, size, name))
        return out


def printable(b):
    s = []
    for enc in ("gbk", "cp932"):
        try:
            t = b.split(b"\0")[0].decode(enc)
            if len(t) >= 2 and all(c.isprintable() or c in "\n\x1b" for c in t):
                s.append(f"{enc}:{t!r}")
        except UnicodeDecodeError:
            pass
    try:
        u = b.decode("utf-16le").split("\0")[0]
        if len(u) >= 2 and all(c.isprintable() for c in u):
            s.append(f"u16:{u!r}")
    except UnicodeDecodeError:
        pass
    return s


def main():
    dm = Dump(sys.argv[1])
    mods = dm.modules()
    exe = next(m for m in mods if m[2].lower().endswith("wo3u.exe"))
    size, loc = dm.streams[6]
    tid, _ = struct.unpack_from("<II", dm.d, loc)
    code, flags, rec, addr, nparams = struct.unpack_from("<IIQQI", dm.d, loc + 8)
    info = struct.unpack_from("<15Q", dm.d, loc + 8 + 32)
    ctx_size, ctx_rva = struct.unpack_from("<II", dm.d, loc + 8 + 152)
    ctx = dm.d[ctx_rva:ctx_rva + ctx_size]
    regs = dict(zip(REGS, struct.unpack_from("<16Q", ctx, 0x78)))
    rip = struct.unpack_from("<Q", ctx, 0xF8)[0]
    print(f"exe base {exe[0]:#x}  code {code:#x}  at {addr:#x} (exe+{addr - exe[0]:#x})  rip exe+{rip - exe[0]:#x}")
    if code == 0xC0000005 and nparams >= 2:
        print("  access:", {0: "read", 1: "write", 8: "execute"}.get(info[0], info[0]), f"{info[1]:#x}")
    code_bytes = dm.read(rip, 32)
    print("  bytes at rip:", code_bytes.hex(" ") if code_bytes else "(not in dump)")
    for r, v in regs.items():
        tag = ""
        if exe[0] <= v < exe[0] + exe[1]:
            tag = f" exe+{v - exe[0]:#x}"
        m = dm.read(v, 96)
        ps = printable(m) if m else []
        print(f"  {r:<4}= {v:#018x}{tag}  {ps[:2]}")
    rsp = regs["RSP"]
    st = dm.read(rsp, 0x400) or b""
    print("  stack return addresses into exe:")
    for i in range(0, len(st) - 7, 8):
        v = struct.unpack_from("<Q", st, i)[0]
        if exe[0] <= v < exe[0] + exe[1]:
            print(f"    [rsp+{i:#05x}] exe+{v - exe[0]:#x}")
    print("  strings pointed to from stack:")
    seen = set()
    for i in range(0, len(st) - 7, 8):
        v = struct.unpack_from("<Q", st, i)[0]
        if v in seen:
            continue
        seen.add(v)
        m = dm.read(v, 128)
        if m:
            ps = printable(m)
            if ps:
                print(f"    [rsp+{i:#05x}] {v:#x} {ps[:2]}")


if __name__ == "__main__":
    main()

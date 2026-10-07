#!/usr/bin/env bash
# Scenario tests of the DLC costume source texts in the common part (LINKFILE_003.BIN), on the game-folder copy only.
# The copy's LINKFILE_003.BIN is a sparse file holding only the patched blocks, copied from the real (untouched) game file.
# Needs: patcher/_cc/WO3U_Steam_KR_Patch.exe (console build) + WO3U_Steam_KR.pack carrying LINKFILE_003.patch.
set -u
W="/c/Emul/Switch/패치유틸.xdeltaUI/work_wo3u_pc"
T="$W/patcher/_testgame/WARRIORS OROCHI 3 Ultimate"
P="$W/patcher/_cc/WO3U_Steam_KR_Patch.exe"
GAME="/c/Program Files (x86)/Steam/steamapps/common/WARRIORS OROCHI 3 Ultimate"
PATCH="$W/patcher/out/LINKFILE_003.patch"
run() { "$P" --folder "$T" --no-pause "$@" | grep -E "\[OK\]|\[!\]|\[\*\]|\[실패\]|의상"; echo "  exit ${PIPESTATUS[0]}"; }
state() { py -3.13 - "$T/LINKFILE_003.BIN" "$PATCH" <<'EOF'
import hashlib, struct, sys
f = open(sys.argv[1], "rb"); d = open(sys.argv[2], "rb").read()
n = struct.unpack_from("<I", d, 8)[0]; p = 12; c = [0, 0, 0]
for _ in range(n):
    e, off, size = struct.unpack_from("<IQI", d, p); oh, nh = d[p + 16:p + 48], d[p + 48:p + 80]; p += 80 + size
    f.seek(off); h = hashlib.sha256(f.read(size)).digest()
    c[0 if h == oh else 1 if h == nh else 2] += 1
print(f"orig {c[0]} ko {c[1]} other {c[2]}")
EOF
}
expect() { local s; s=$(state); [ "$s" = "$1" ] && echo "  003 $2: PASS ($s)" || echo "  003 $2: FAIL ($s)"; }

rm -f "$T/LINKFILE_003.BIN"; py -3.13 -c "open(__import__('sys').argv[1],'wb').close()" "$T/LINKFILE_003.BIN"
fsutil sparse setflag "$(cygpath -w "$T/LINKFILE_003.BIN")" >/dev/null
py -3.13 - "$GAME/LINKFILE_003.BIN" "$T/LINKFILE_003.BIN" "$PATCH" <<'EOF'
import os, struct, sys
src, dst, patch = sys.argv[1], sys.argv[2], open(sys.argv[3], "rb").read()
n = struct.unpack_from("<I", patch, 8)[0]; p = 12
with open(src, "rb") as s, open(dst, "r+b") as t:
    for _ in range(n):
        e, off, size = struct.unpack_from("<IQI", patch, p); p += 80 + size
        s.seek(off); t.seek(off); t.write(s.read(size))
    # the real game may already carry the Korean blocks: take the originals from its backup when there is one
    bk = os.path.join(os.path.dirname(src), "WO3U_KR_003.wo3u-backup")
    if os.path.exists(bk):
        b = open(bk, "rb").read(); assert b[:8] == b"WO3UB003"
        cnt = struct.unpack_from("<i", b, 8)[0]; q = 12
        for _ in range(cnt):
            off, ln = struct.unpack_from("<qi", b, q); q += 12
            t.seek(off); t.write(b[q:q + ln]); q += ln
    t.truncate(os.path.getsize(src))
EOF
rm -f "$T/WO3U_KR_003.wo3u-backup"
N=$(py -3.13 -c "import struct,sys;print(struct.unpack_from('<I',open(sys.argv[1],'rb').read(12),8)[0])" "$PATCH")
expect "orig $N ko 0 other 0" "fake file original"

echo "== 1 patch: Korean data + costume texts";   run --yes;            expect "orig 0 ko $N other 0" korean
[ -f "$T/WO3U_KR_003.wo3u-backup" ] && echo "  backup made: PASS" || echo "  backup made: FAIL"
echo "== 2 verify";                               run --verify-only
echo "== 3 patch again: nothing to do";           run --yes;            expect "orig 0 ko $N other 0" "still korean"
echo "== 4 restore";                              run --restore --yes;  expect "orig $N ko 0 other 0" restored
echo "== 5 one block changed by something else: left alone"
py -3.13 - "$T/LINKFILE_003.BIN" "$PATCH" <<'EOF'
import struct, sys
d = open(sys.argv[2], "rb").read(); e, off, size = struct.unpack_from("<IQI", d, 12)
f = open(sys.argv[1], "r+b"); f.seek(off + size - 1); f.write(b"\x7f")
EOF
run --yes; expect "orig 0 ko $((N - 1)) other 1" "one other"
echo "== 6 restore keeps the foreign block";      run --restore --yes;  expect "orig $((N - 1)) ko 0 other 1" "restored, one other"
echo "== 7 cleanup"; rm -f "$T/LINKFILE_003.BIN" "$T/WO3U_KR_003.wo3u-backup"; echo "  removed"

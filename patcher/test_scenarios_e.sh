#!/usr/bin/env bash
# Scenario tests of the optional soldier-aggression setting (--soldier-ai / --no-soldier-ai), on the game-folder copy only.
# LINKFILE_000.BIN in the copy is a short file holding the real bytes up to the end of the unit table (0x44CDA + 88240).
# Needs: patcher/_cc/WO3U_Steam_KR_Patch.exe (console build) + WO3U_Steam_KR.pack of the build in $B.
set -u
W="/c/Emul/Switch/패치유틸.xdeltaUI/work_wo3u_pc"
T="$W/patcher/_testgame/WARRIORS OROCHI 3 Ultimate"
P="$W/patcher/_cc/WO3U_Steam_KR_Patch.exe"
B="$W/build/${BUILD:-test25}"
GAME="/c/Program Files (x86)/Steam/steamapps/common/WARRIORS OROCHI 3 Ultimate"
VANILLA=A6B62541DBE6CEF5
TARGET=791E7F8135942A89
blk() { py -3.13 -c "import hashlib,sys;f=open(sys.argv[1],'rb');f.seek(0x44CDA);print(hashlib.sha256(f.read(88240)).hexdigest()[:16].upper())" "$T/LINKFILE_000.BIN"; }
run() { "$P" --folder "$T" --no-pause "$@" | grep -E "\[OK\]|\[!\]|\[\*\]|\[실패\]|병사"; echo "  exit ${PIPESTATUS[0]}"; }
expect() { [ "$(blk)" = "$1" ] && echo "  block $2: PASS" || echo "  block $2: FAIL ($(blk))"; }

# fresh vanilla unit table from the saved original block (the real game currently has the setting applied)
py -3.13 - "$GAME" "$T" <<'EOF'
import sys
from pathlib import Path
g, t = Path(sys.argv[1]), Path(sys.argv[2])
head = open(g / "LINKFILE_000.BIN", "rb").read(0x44CDA)
(t / "LINKFILE_000.BIN").write_bytes(head + (g / "WO3U_soldier_ai.orig").read_bytes())
EOF
expect $VANILLA "fake file vanilla"

echo "== 1 patch without option: setting untouched";  run --yes;                expect $VANILLA vanilla
echo "== 2 --soldier-ai";                             run --yes --soldier-ai;   expect $TARGET applied
echo "== 3 verify shows it";                          run --verify-only
echo "== 4 --soldier-ai again: no change";            run --yes --soldier-ai;   expect $TARGET applied
echo "== 5 patch without option keeps it";            run --yes;                expect $TARGET applied
echo "== 6 --no-soldier-ai";                          run --yes --no-soldier-ai; expect $VANILLA vanilla
echo "== 7 --soldier-ai then restore -> also reverted"; run --yes --soldier-ai >/dev/null; run --restore --yes; expect $VANILLA vanilla
echo "== 8 foreign unit mod: --soldier-ai skips, file untouched"
py -3.13 -c "import sys;f=open(sys.argv[1],'r+b');f.seek(0x44CDA+32);f.write(b'\xff\xff')" "$T/LINKFILE_000.BIN"
before=$(blk); run --yes --soldier-ai; [ "$(blk)" = "$before" ] && echo "  untouched: PASS" || echo "  untouched: FAIL"
run --yes --no-soldier-ai; [ "$(blk)" = "$before" ] && echo "  untouched (off): PASS" || echo "  untouched (off): FAIL"
echo "== 9 cleanup"; run --restore --yes >/dev/null; rm -f "$T/LINKFILE_000.BIN"; ls "$T" | grep -c LINKFILE_000 | sed 's/^0$/  removed: PASS/'

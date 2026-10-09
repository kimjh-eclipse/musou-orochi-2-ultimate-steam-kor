#!/usr/bin/env bash
# Scenario tests: soldier option + officer option on the same unit table (independent on/off), on the game-folder copy.
# Needs: patcher/_cc/WO3U_Steam_KR_Patch.exe (console build) + pack; the real game's WO3U_soldier_ai.orig (vanilla block).
set -u
W="/c/Emul/Switch/패치유틸.xdeltaUI/work_wo3u_pc"
T="$W/patcher/_testgame/WARRIORS OROCHI 3 Ultimate"
P="$W/patcher/_cc/WO3U_Steam_KR_Patch.exe"
GAME="/c/Program Files (x86)/Steam/steamapps/common/WARRIORS OROCHI 3 Ultimate"
run() { "$P" --folder "$T" --no-pause "$@" | grep -E "\[실패\]|\[!\]" ; echo "  exit ${PIPESTATUS[0]}"; }
st() {  # "S<0|1> O<0|1>" from the verify output
  local v; v=$("$P" --folder "$T" --no-pause --verify-only)
  local s=0 o=0
  echo "$v" | grep -q "'병사 공격성 강화'가 적용되어" && s=1
  echo "$v" | grep -q "'장수 공격성 한 단계 올리기'가 적용되어" && o=1
  echo "$v" | grep -q "다른 프로그램으로 수정되어" && s=X && o=X
  echo "S$s O$o"
}
expect() { local s; s=$(st); [ "$s" = "$1" ] && echo "  $2: PASS ($s)" || echo "  $2: FAIL ($s)"; }
py -3.13 - "$GAME" "$T" <<'EOF'
import sys
from pathlib import Path
g, t = Path(sys.argv[1]), Path(sys.argv[2])
head = open(g / "LINKFILE_000.BIN", "rb").read(0x44CDA)
(t / "LINKFILE_000.BIN").write_bytes(head + (g / "WO3U_soldier_ai.orig").read_bytes())
EOF
expect "S0 O0" "fake file vanilla"
echo "== 1 officer only";            run --yes --officer-ai;                   expect "S0 O1" "officer on"
echo "== 2 add soldier";             run --yes --soldier-ai;                   expect "S1 O1" "both on (officer kept when omitted)"
echo "== 3 soldier off";             run --yes --no-soldier-ai;                expect "S0 O1" "officer kept"
echo "== 4 both again, officer off"; run --yes --soldier-ai --no-officer-ai;   expect "S1 O0" "soldier only"
echo "== 5 both on, restore";        run --yes --soldier-ai --officer-ai >/dev/null; run --restore --yes; expect "S0 O0" "restored"
echo "== 6 foreign change: both skipped"
py -3.13 -c "import sys;f=open(sys.argv[1],'r+b');f.seek(0x44CDA+5);f.write(b'\x99')" "$T/LINKFILE_000.BIN"
run --yes --soldier-ai --officer-ai; expect "SX OX" "foreign left alone"
echo "== 7 cleanup"; run --restore --yes >/dev/null; rm -f "$T/LINKFILE_000.BIN"; echo "  removed"

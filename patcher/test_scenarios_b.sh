#!/usr/bin/env bash
# Scenario tests of the v20260927b patcher on the game-folder copy (never the real game folder).
# Start state: v20260927 applied with its backup (what an existing user has).
set -u
W="/c/Emul/Switch/패치유틸.xdeltaUI/work_wo3u_pc"
T="$W/patcher/_testgame/WARRIORS OROCHI 3 Ultimate"
P="$W/release/v20260927b/WO3U_Steam_KR_v20260927b/WO3U_Steam_KR_Patch.exe"
B="$W/build/test15"
DLL="$W/patcher/dll/out/mode3/dinput8.dll"
ORIG="$W/backup/original"
h() { sha256sum "$1" | cut -c1-16; }
run() { "$P" --folder "$T" --no-pause "$@" | grep -E "\[OK\]|\[!\]|\[실패\]|이전 패치|적용된 상태|원본 상태"; echo "  exit ${PIPESTATUS[0]}"; }
check() {  # expected: target | source
  local want=$1 ok=1
  if [ "$want" = target ]; then
    [ "$(h "$T/LINKIDX_CHS.BIN")" = "$(h "$B/LINKIDX_CHS.BIN")" ] || ok=0
    [ "$(h "$T/LINKFILE_CHS.BIN")" = "$(h "$B/LINKFILE_CHS.BIN")" ] || ok=0
    [ -f "$T/dinput8.dll" ] && [ "$(h "$T/dinput8.dll")" = "$(h "$DLL")" ] || ok=0
  else
    [ "$(h "$T/LINKIDX_CHS.BIN")" = "$(h "$ORIG/LINKIDX_CHS.BIN")" ] || ok=0
    [ "$(h "$T/LINKFILE_CHS.BIN")" = "$(h "$ORIG/LINKFILE_CHS.BIN")" ] || ok=0
    [ ! -f "$T/dinput8.dll" ] || ok=0
  fi
  [ $ok = 1 ] && echo "  CHECK $want: PASS" || echo "  CHECK $want: FAIL"
}
echo "== 1 update v20260927 -> v20260927b";  run --yes; check target
echo "== 2 verify";                            run --verify-only
echo "== 3 run again (already applied)";       run --yes; check target
echo "== 4 dll deleted -> reinstall only";     rm -f "$T/dinput8.dll"; run --yes; check target
echo "== 5 restore";                           run --restore --yes; check source
echo "== 6 foreign dinput8.dll -> refuse";     printf 'other mod dll' > "$T/dinput8.dll"; run --yes; [ "$(cat "$T/dinput8.dll")" = "other mod dll" ] && echo "  foreign dll untouched: PASS" || echo "  foreign dll untouched: FAIL"; rm -f "$T/dinput8.dll"; check source
echo "== 7 apply from original";               run --yes; check target
ls "$T"

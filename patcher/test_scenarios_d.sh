#!/usr/bin/env bash
# Scenario tests of the chain option (default) for another program's dinput8.dll, on the game-folder copy only.
# Needs: patcher/_cc/WO3U_Steam_KR_Patch.exe + WO3U_Steam_KR.pack of the build in $B.
set -u
W="/c/Emul/Switch/패치유틸.xdeltaUI/work_wo3u_pc"
T="$W/patcher/_testgame/WARRIORS OROCHI 3 Ultimate"
P="$W/patcher/_cc/WO3U_Steam_KR_Patch.exe"
B="$W/build/${BUILD:-test18}"
DLL="$W/patcher/dll/out/mode3/dinput8.dll"
ORIG="$W/backup/original"
FOREIGN="other mod dll"
h() { sha256sum "$1" | cut -c1-16; }
run() { "$P" --folder "$T" --no-pause "$@" | grep -E "\[OK\]|\[!\]|\[\*\]|\[실패\]|건너|보관|되돌|이어서|적용된 상태|원본 상태"; echo "  exit ${PIPESTATUS[0]}"; }
data() {
  if [ "$1" = target ]; then [ "$(h "$T/LINKIDX_CHS.BIN")" = "$(h "$B/LINKIDX_CHS.BIN")" ] && [ "$(h "$T/LINKFILE_CHS.BIN")" = "$(h "$B/LINKFILE_CHS.BIN")" ] && echo 1 || echo 0
  else [ "$(h "$T/LINKIDX_CHS.BIN")" = "$(h "$ORIG/LINKIDX_CHS.BIN")" ] && [ "$(h "$T/LINKFILE_CHS.BIN")" = "$(h "$ORIG/LINKFILE_CHS.BIN")" ] && echo 1 || echo 0; fi
}
dll() {
  case $1 in
    ours) [ -f "$T/dinput8.dll" ] && [ "$(h "$T/dinput8.dll")" = "$(h "$DLL")" ] && echo 1 || echo 0 ;;
    foreign) [ -f "$T/dinput8.dll" ] && [ "$(cat "$T/dinput8.dll")" = "$FOREIGN" ] && echo 1 || echo 0 ;;
    none) [ ! -f "$T/dinput8.dll" ] && echo 1 || echo 0 ;;
  esac
}
chain() { [ -f "$T/dinput8_wo3u_chain.dll" ] && [ "$(cat "$T/dinput8_wo3u_chain.dll")" = "$FOREIGN" ] && echo 1 || echo 0; }
nochain() { [ ! -f "$T/dinput8_wo3u_chain.dll" ] && echo 1 || echo 0; }
noorig() { ls "$T" | grep -q "wo3u-orig" && echo 0 || echo 1; }
expect() { local name=$1; shift; local all=1; for v in "$@"; do [ "$v" = 1 ] || all=0; done; [ $all = 1 ] && echo "  $name: PASS" || echo "  $name: FAIL ($*)"; }

echo "== 1 apply (update to this build)";          run --yes;                 expect "data target, ours" $(data target) $(dll ours) $(nochain)
echo "== 2 restore";                               run --restore --yes;       expect "data source, no dll" $(data source) $(dll none)
printf "$FOREIGN" > "$T/dinput8.dll"
echo "== 3 foreign + --yes -> chain (default)";    run --yes;                 expect "ours + chain" $(data target) $(dll ours) $(chain) $(noorig)
echo "== 4 verify shows chain";                    run --verify-only
echo "== 5 run again: nothing changes";            run --yes;                 expect "still ours + chain" $(data target) $(dll ours) $(chain)
echo "== 6 restore -> foreign back";               run --restore --yes;       expect "data source, foreign back" $(data source) $(dll foreign) $(nochain)
echo "== 7 interactive Enter (default chain) + Y"; printf '\r\nY\r\n' | run;  expect "ours + chain" $(data target) $(dll ours) $(chain)
echo "== 8 mod reinstalled over ours -> chain again (old chain kept with timestamp)"
printf "$FOREIGN" > "$T/dinput8.dll"
run --yes;  expect "ours + chain" $(data target) $(dll ours) $(chain)
ls "$T" | grep -i "chain"
echo "== 9 restore (latest chain back)";           run --restore --yes;       expect "foreign back" $(data source) $(dll foreign) $(nochain)
rm -f "$T"/dinput8_wo3u_chain.*.dll
echo "== 10 --overwrite-dll still works";          run --yes --overwrite-dll; expect "ours, orig kept, no chain" $(data target) $(dll ours) $(nochain)
echo "== 11 restore";                              run --restore --yes;       expect "foreign back" $(data source) $(dll foreign) $(noorig)
echo "== 12 cleanup: remove foreign, apply";       rm -f "$T/dinput8.dll"; run --yes; expect "data target, ours" $(data target) $(dll ours) $(nochain) $(noorig)
ls "$T"

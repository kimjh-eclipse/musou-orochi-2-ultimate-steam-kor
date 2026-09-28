#!/usr/bin/env bash
# Scenario tests of the foreign-dinput8.dll policy (ask: overwrite / skip) on the game-folder copy only.
# Start state: whatever an earlier scenario run left (v20260927b applied with its backup).
set -u
W="/c/Emul/Switch/패치유틸.xdeltaUI/work_wo3u_pc"
T="$W/patcher/_testgame/WARRIORS OROCHI 3 Ultimate"
P="$W/patcher/_cc/WO3U_Steam_KR_Patch.exe"
B="$W/build/test16"
DLL="$W/patcher/dll/out/mode3/dinput8.dll"
ORIG="$W/backup/original"
FOREIGN="other mod dll"
h() { sha256sum "$1" | cut -c1-16; }
run() { "$P" --folder "$T" --no-pause "$@" | grep -E "\[OK\]|\[!\]|\[\*\]|\[실패\]|건너|보관|되돌|적용된 상태|원본 상태"; echo "  exit ${PIPESTATUS[0]}"; }
data() {  # target | source
  local ok=1
  if [ "$1" = target ]; then
    [ "$(h "$T/LINKIDX_CHS.BIN")" = "$(h "$B/LINKIDX_CHS.BIN")" ] && [ "$(h "$T/LINKFILE_CHS.BIN")" = "$(h "$B/LINKFILE_CHS.BIN")" ] || ok=0
  else
    [ "$(h "$T/LINKIDX_CHS.BIN")" = "$(h "$ORIG/LINKIDX_CHS.BIN")" ] && [ "$(h "$T/LINKFILE_CHS.BIN")" = "$(h "$ORIG/LINKFILE_CHS.BIN")" ] || ok=0
  fi
  echo $ok
}
dll() {  # ours | foreign | none
  case $1 in
    ours) [ -f "$T/dinput8.dll" ] && [ "$(h "$T/dinput8.dll")" = "$(h "$DLL")" ] && echo 1 || echo 0 ;;
    foreign) [ -f "$T/dinput8.dll" ] && [ "$(cat "$T/dinput8.dll")" = "$FOREIGN" ] && echo 1 || echo 0 ;;
    none) [ ! -f "$T/dinput8.dll" ] && echo 1 || echo 0 ;;
  esac
}
kept() { [ -f "$T/dinput8.dll.wo3u-orig" ] && [ "$(cat "$T/dinput8.dll.wo3u-orig")" = "$FOREIGN" ] && echo 1 || echo 0; }
nokept() { ls "$T" | grep -c "wo3u-orig" | sed 's/^0$/1/;t;s/.*/0/'; }
expect() { local name=$1; shift; local all=1; for v in "$@"; do [ "$v" = 1 ] || all=0; done; [ $all = 1 ] && echo "  $name: PASS" || echo "  $name: FAIL ($*)"; }

echo "== 1 update v20260927b -> v20260928";        run --yes;                  expect "data target, ours" $(data target) $(dll ours) $(nokept)
echo "== 2 restore";                                run --restore --yes;        expect "data source, no dll" $(data source) $(dll none) $(nokept)
printf "$FOREIGN" > "$T/dinput8.dll"
echo "== 3 foreign + --yes -> skip";                run --yes;                  expect "data target, foreign untouched" $(data target) $(dll foreign) $(nokept)
echo "== 4 verify shows foreign";                   run --verify-only
echo "== 5 foreign + --overwrite-dll";              run --yes --overwrite-dll;  expect "ours installed, foreign kept" $(data target) $(dll ours) $(kept)
echo "== 6 restore -> foreign back";                run --restore --yes;        expect "data source, foreign restored" $(data source) $(dll foreign) $(nokept)
echo "== 7 foreign + --skip-dll";                   run --yes --skip-dll;       expect "data target, foreign untouched" $(data target) $(dll foreign) $(nokept)
echo "== 8 restore with foreign in place";          run --restore --yes;        expect "data source, foreign untouched" $(data source) $(dll foreign) $(nokept)
echo "== 9 interactive: O then Y";                  printf 'O\r\nY\r\n' | run;  expect "ours installed, foreign kept" $(data target) $(dll ours) $(kept)
echo "== 10 other mod reinstalled over ours, overwrite again (old kept gets a timestamp name)"
printf "$FOREIGN" > "$T/dinput8.dll"
run --yes --overwrite-dll;  expect "ours, kept=foreign" $(data target) $(dll ours) $(kept)
ls "$T" | grep "wo3u-orig"
echo "== 11 interactive cancel: N";                 run --restore --yes >/dev/null; printf "$FOREIGN" > "$T/dinput8.dll.tmpf"
rm -f "$T"/dinput8.dll.*.wo3u-orig; mv "$T/dinput8.dll.tmpf" "$T/dinput8.dll"
printf 'N\r\n' | run;       expect "nothing changed" $(data source) $(dll foreign)
echo "== 12 cleanup: remove foreign, apply";        rm -f "$T/dinput8.dll"; run --yes; expect "data target, ours" $(data target) $(dll ours) $(nokept)
ls "$T"

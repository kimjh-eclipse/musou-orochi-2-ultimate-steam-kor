#!/usr/bin/env bash
# Re-run of scenarios 2-4 of test_scenarios_c.sh (their output was cut): restore, foreign + --yes -> skip, verify.
set -u
source <(sed -n '/^W=/,/^expect()/p' "$(dirname "$0")/test_scenarios_c.sh")
echo "== 2 restore";                      run --restore --yes;   expect "data source, no dll" $(data source) $(dll none) $(nokept)
printf "$FOREIGN" > "$T/dinput8.dll"
echo "== 3 foreign + --yes -> skip";      run --yes;             expect "data target, foreign untouched" $(data target) $(dll foreign) $(nokept)
echo "== 4 verify shows foreign";         run --verify-only
echo "== cleanup";                        rm -f "$T/dinput8.dll"; run --yes; expect "data target, ours" $(data target) $(dll ours) $(nokept)

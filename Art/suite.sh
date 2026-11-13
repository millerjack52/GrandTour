#!/usr/bin/env bash
# One-call headless test suite. Runs the *_test.bat files and prints one line per test.
#   bash Art/suite.sh              all 28 tests
#   bash Art/suite.sh drivetrain terrain   just those
#   bash Art/suite.sh -q ...       quiet: only the summary and any FAIL detail
# Each test's .bat ends in `pause`; stdin from /dev/null makes it return at once.
# The .bat path goes through cygpath -w into a variable (a backslash before a $ in a
# bash string never runs and leaves a stale log), and each log's time is checked
# against the start so a stale log cannot pass as a rerun.
set -u
ART="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$ART/.." && pwd)"
LOGS="$ROOT/Saved/Logs"
QUIET=0
if [ "${1:-}" = "-q" ]; then QUIET=1; shift; fi
if [ $# -eq 0 ]; then
  set -- base biome body bodystate door dressing_toolkit drive drivetrain env grip hazard leg loop loot mud onfoot proving rough route_clear spray surface terrain tour track veg water weather winch
fi
pass=0; fail=0; failed=""
for t in "$@"; do
  bat="$ART/${t}_test.bat"
  if [ ! -f "$bat" ]; then echo "?? $t: no ${t}_test.bat"; fail=$((fail+1)); failed="$failed $t"; continue; fi
  log=$(grep -o -- '-log=[A-Za-z0-9_]*\.log' "$bat" | head -1 | cut -d= -f2)
  start=$(date +%s)
  wbat=$(cygpath -w "$bat")
  cmd //c "$wbat" < /dev/null > /dev/null 2>&1
  logf="$LOGS/$log"
  if [ ! -f "$logf" ]; then echo "FAIL $t: no log $log"; fail=$((fail+1)); failed="$failed $t"; continue; fi
  mtime=$(stat -c %Y "$logf")
  if [ "$mtime" -lt "$start" ]; then echo "FAIL $t: stale log (did not run)"; fail=$((fail+1)); failed="$failed $t"; continue; fi
  line=$(grep "GTDRIVETEST_RESULT" "$logf" | tail -1 | sed 's/^.*GTDRIVETEST_RESULT //')
  secs=$(( $(date +%s) - start ))
  case "$line" in
    PASS*) pass=$((pass+1)); [ $QUIET -eq 0 ] && echo "PASS $t (${secs}s): ${line#PASS }" | cut -c1-220 ;;
    *)
      fail=$((fail+1)); failed="$failed $t"
      echo "FAIL $t (${secs}s): ${line:-no GTDRIVETEST_RESULT line}" | cut -c1-300
      echo "  --- last GTDRIVETEST lines of $log:"
      grep "GTDRIVETEST" "$logf" | tail -12 | sed 's/^\[[^]]*\]\[[^]]*\]//' | cut -c1-240 | sed 's/^/  /'
      grep -i "error\|fatal\|assert" "$logf" | grep -v "GTDRIVETEST" | tail -4 | cut -c1-200 | sed 's/^  err: /  err: /'
      ;;
  esac
done
echo "== suite: $pass PASS, $fail FAIL${failed:+ (failed:$failed)}"
[ $fail -eq 0 ]

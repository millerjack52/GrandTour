#!/usr/bin/env bash
# Look stage L6 (docs/LOOK_PLAN.md L6, docs/VEHICLE_BUILD_SYSTEM.md section 57): bakes the painted-dab normal tile
# Art/Textures/Painted/T_GT_DabTile_N.png from a flat 2 x 2 m plane through the GT Paint pipeline (the preset as it is,
# the owner's OW Painterly Normal Baker) and measures its seam.
#   bash Art/make_dab_tile.sh
# Blender 5.1 in the background with --factory-startup (as Art/blender_test.sh): the owner's preferences stay out and
# GT Paint imports the baker from its folder. The bake's own files go to a temp folder; only the _N is kept. Full log:
# Saved/Logs/make_dab_tile.log; the GTDABTILE lines are printed here. A script file so the Windows paths survive MSYS.
set -u
ART="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$ART/.." && pwd)"
BLENDER="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
LOG="$ROOT/Saved/Logs/make_dab_tile.log"
WORK="${TMP:-${TEMP:-/tmp}}"
WORK="$(cygpath -u "$WORK")/gt_dab_tile"
mkdir -p "$WORK" "$ROOT/Saved/Logs"
start=$(date +%s)
"$BLENDER" -b --factory-startup --python-exit-code 1 --python "$(cygpath -w "$ART/tools/make_dab_tile.py")" \
  -- "$(cygpath -w "$WORK")" > "$LOG" 2>&1
code=$?
grep "GTDABTILE" "$LOG"
grep -E "^Error|Traceback|Error:" "$LOG" | head -8
echo "== make_dab_tile exit $code ($(( $(date +%s) - start )) s), log $LOG"
exit $code

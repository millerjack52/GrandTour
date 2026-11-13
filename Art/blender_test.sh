#!/usr/bin/env bash
# The GT Paint addon's headless test (docs/LOOK_PLAN.md L1, docs/VEHICLE_BUILD_SYSTEM.md section 55).
#   bash Art/blender_test.sh
# Copies Art/rangerover.blend (the owner's blockout, never opened itself) to a temp folder, runs Blender 5.1 in the
# background on the copy with Art/Blender/tests/test_gt_paint.py, which bakes and exports TestCube, TestBox and
# TestCar into Art/Export/<Asset>/. Full log: Saved/Logs/blender_test.log; the GTPAINT_TEST lines are printed here.
# --factory-startup: the owner's preferences and add-ons (the blender_mcp addon among them) stay out of the test.
# The owner's OW Painterly Normal Baker (Bake's _N) is then not registered: GT Paint imports it from its folder
# (%APPDATA%/Blender Foundation/Blender/5.1/extensions/user_default/ow_painterly_normal_baker) without writing there.
# A script file, not typed inline, so the Windows paths survive MSYS.
set -u
ART="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$ART/.." && pwd)"
BLENDER="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
LOG="$ROOT/Saved/Logs/blender_test.log"
WORK="${TMP:-${TEMP:-/tmp}}"
WORK="$(cygpath -u "$WORK")/gt_paint_test"
mkdir -p "$WORK" "$ROOT/Saved/Logs"
COPY="$WORK/rangerover_copy.blend"
cp -f "$ART/rangerover.blend" "$COPY" || { echo "GTPAINT_TEST could not copy the blockout"; exit 1; }
start=$(date +%s)
"$BLENDER" -b --factory-startup "$(cygpath -w "$COPY")" --python-exit-code 1 --python "$(cygpath -w "$ART/Blender/tests/test_gt_paint.py")" \
  -- "$(cygpath -w "$ART/Export")" > "$LOG" 2>&1
code=$?
grep "GTPAINT_TEST" "$LOG"
grep -E "^Error|Traceback|Error:" "$LOG" | head -8
echo "== blender_test exit $code ($(( $(date +%s) - start )) s), log $LOG"
exit $code

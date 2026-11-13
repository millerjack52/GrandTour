#!/usr/bin/env bash
# One-call native plant kit runner (docs/NATIVE_PLANT_KIT_PLAN.md).
#   bash Art/build_native_plants.sh [bush|open|floor|verge|farm|grass|patch|all]
# Builds the set in Blender 5.1.2, round-trips every FBX in the manifest, logs to
# Saved/Logs/native_plants_<set>.log and prints the manifest summary, the validation line and
# the render paths. Exits non-zero when a build or the validation fails. Unreal can stay open.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLENDER="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
SET="${1:-bush}"
case "$SET" in bush|open|floor|verge|farm|grass|patch|all) ;; *) echo "usage: bash Art/build_native_plants.sh [bush|open|floor|verge|farm|grass|patch|all]"; exit 2;; esac
mkdir -p "$ROOT/Saved/Logs"
status=0

blender_run() { # script log [script args]
  local script="$1" log="$2"; shift 2
  "$BLENDER" -b --factory-startup --python-exit-code 1 --python "$script" -- "$@" >> "$log" 2>&1
}

build_set() { # name script ok-token
  local name="$1" script="$ROOT/Art/Blender/$2" token="$3"
  local log="$ROOT/Saved/Logs/native_plants_${name}.log"
  if [ ! -f "$script" ]; then
    echo "SKIP $name: Art/Blender/$2 does not exist yet"
    return 0
  fi
  : > "$log"
  local t0=$SECONDS
  echo "== $name: build $2 (log $log)"
  if ! blender_run "$script" "$log" || ! grep -q "$token" "$log"; then
    echo "FAIL $name: build"; grep -E "Error|Traceback|AssertionError|File \"" "$log" | tail -8; status=1; return 1
  fi
  echo "== $name: validate_native_plants.py --set $name"
  if ! blender_run "$ROOT/Art/Blender/validate_native_plants.py" "$log" --set "$name" || ! grep -q NATIVE_VALIDATION_OK "$log"; then
    echo "FAIL $name: validation"; grep -E "VALIDATION_FAIL|Error|Traceback" "$log" | tail -12; status=1; return 1
  fi
  grep "^SUMMARY" "$log" | sed 's/^SUMMARY /  /'
  grep "$token" "$log"
  grep "NATIVE_VALIDATION_OK" "$log"
  grep "^RENDER " "$log" | sed 's/^RENDER /  render: /'
  echo "== $name: done in $((SECONDS - t0)) s"
}

if [ "$SET" = bush ] || [ "$SET" = all ]; then
  build_set bush build_native_bush.py NATIVE_BUSH_BUILD_OK
fi
if [ "$SET" = open ] || [ "$SET" = all ]; then
  build_set open build_native_open.py NATIVE_OPEN_BUILD_OK
fi
if [ "$SET" = floor ] || [ "$SET" = all ]; then
  build_set floor build_southland_floor.py NATIVE_FLOOR_BUILD_OK
fi
if [ "$SET" = verge ] || [ "$SET" = all ]; then
  build_set verge build_southland_verge.py NATIVE_VERGE_BUILD_OK
fi
if [ "$SET" = farm ] || [ "$SET" = all ]; then
  build_set farm build_southland_farm.py NATIVE_FARM_BUILD_OK
fi
if [ "$SET" = grass ] || [ "$SET" = all ]; then
  build_set grass build_southland_grass.py NATIVE_GRASS_BUILD_OK
fi
if [ "$SET" = patch ] || [ "$SET" = all ]; then
  build_set patch build_southland_patch.py NATIVE_PATCH_BUILD_OK
fi
if [ "$SET" = all ] && [ $status -eq 0 ]; then
  # one round trip over the whole shared manifest (bush, open, floor, verge, farm, grass and patch sets) -> validation-report.json
  log="$ROOT/Saved/Logs/native_plants_all.log"; : > "$log"
  echo "== all: validate_native_plants.py (every FBX in the manifest)"
  if blender_run "$ROOT/Art/Blender/validate_native_plants.py" "$log" && grep -q NATIVE_VALIDATION_OK "$log"; then
    grep "NATIVE_VALIDATION_OK" "$log"
  else
    echo "FAIL all: validation"; grep -E "VALIDATION_FAIL|Error|Traceback" "$log" | tail -12; status=1
  fi
fi
exit $status

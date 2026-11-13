#!/usr/bin/env bash
# BT1 v02: build and review the three smoothness variants, then tub-variants.png.
# Usage: bash run_bt1_v02.sh [P1 P4 P16]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
ROOT="C:/GrandTour/Art/Export/VehicleTools/impreza-builder-bt1-v02"
VARIANTS="${@:-P1 P4 P16}"
export BT_VERSION=v02
for V in $VARIANTS; do
  export BT_VARIANT=$V
  mkdir -p "$ROOT/$V/debug"
  echo "== $V fields"
  python "$HERE/bt1_fields.py" > "$ROOT/$V/bt1-fields.log" 2>&1
  python "$HERE/bt1_debug.py" >> "$ROOT/$V/bt1-fields.log" 2>&1
  echo "== $V blender"
  "$BLENDER" -b --python-exit-code 1 --python "$HERE/bt1_blender.py" > "$ROOT/$V/bt1-blender.log" 2>&1
  echo "== $V compose"
  python "$HERE/bt1_compose.py"
done
python "$HERE/bt1_variants.py"

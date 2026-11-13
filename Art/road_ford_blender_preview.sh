#!/usr/bin/env bash
# Offline source/export/render work only; safe while Unreal holds the imported assets.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
  --python "$(cygpath -w "$ROOT/Art/Blender/build_road_ford_style.py")" > "$ROOT/Saved/Logs/road_ford_style_blender.log" 2>&1
grep 'ROAD_FORD_STYLE_OK' "$ROOT/Saved/Logs/road_ford_style_blender.log"

#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if tasklist //FO CSV 2>/dev/null | grep -qiE 'UnrealEditor|GrandTour.exe|FarCry'; then
  echo 'ROAD_FORD_STYLE blocked: an editor or game is running'; exit 2
fi
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
  --python "$(cygpath -w "$ROOT/Art/Blender/build_road_ford_style.py")" > "$ROOT/Saved/Logs/road_ford_style_blender.log" 2>&1
grep 'ROAD_FORD_STYLE_OK' "$ROOT/Saved/Logs/road_ford_style_blender.log"

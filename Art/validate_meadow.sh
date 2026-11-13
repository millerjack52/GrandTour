#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLENDER='/c/Program Files/Blender Foundation/Blender 5.1/blender.exe'
"$BLENDER" -b --factory-startup "$ROOT/Art/Export/RoadFordStyle/RoadFordStyle.blend" --python-exit-code 1 --python "$ROOT/Art/Blender/validate_ground_material.py" > "$ROOT/Saved/Logs/ground_validation.log" 2>&1
"$BLENDER" -b --factory-startup --python-exit-code 1 --python "$ROOT/Art/Blender/save_grass_library.py" > "$ROOT/Saved/Logs/grass_library_validation.log" 2>&1
echo 'MEADOW_VALIDATION_OK'

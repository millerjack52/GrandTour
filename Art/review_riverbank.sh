#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$(cygpath -w "$ROOT/Art/Blender/review_riverbank_iteration.py")" -- "${1:-pass-01}" > "$ROOT/Saved/Logs/review_riverbank.log" 2>&1
grep 'TREE_REVIEW_OK' "$ROOT/Saved/Logs/review_riverbank.log"

#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$(cygpath -w "$ROOT/Art/Blender/finish_riverbank_library_review.py")" > "$ROOT/Saved/Logs/render_riverbank_library.log" 2>&1
grep 'LIBRARY_REVIEW_OK' "$ROOT/Saved/Logs/render_riverbank_library.log"

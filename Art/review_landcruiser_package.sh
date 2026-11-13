#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$(cygpath -w "$ROOT/Art/Blender/review_landcruiser_package.py")" -- "$@" > "$ROOT/Saved/Logs/lc_package_review.log" 2>&1
grep -E 'LC_REVIEW_' "$ROOT/Saved/Logs/lc_package_review.log"

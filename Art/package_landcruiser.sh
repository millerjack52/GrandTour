#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$(cygpath -w "$ROOT/Art/Blender/package_landcruiser.py")" -- "$@" > "$ROOT/Saved/Logs/lc_package.log" 2>&1
grep -E 'LC_PACKAGE_' "$ROOT/Saved/Logs/lc_package.log"

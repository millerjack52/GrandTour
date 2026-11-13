#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-R1}"
VIEWS="${2:-front,rear,side,cockpit}"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$(cygpath -w "$ROOT/Art/Blender/rebuild_landcruiser.py")" -- --version "$VERSION" --views "$VIEWS" > "$ROOT/Saved/Logs/lc_rebuild_${VERSION}.log" 2>&1
grep -E 'LC_REBUILD_' "$ROOT/Saved/Logs/lc_rebuild_${VERSION}.log"

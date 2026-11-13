#!/usr/bin/env bash
# Isolated source modelling and CPU renders; does not launch Unreal or touch the owner source.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-01}"
VIEWS="${2:-front,rear,side,cockpit}"
SAMPLES="${3:-32}"
mkdir -p "$ROOT/Saved/Logs"
LOG="$ROOT/Saved/Logs/landcruiser_${VERSION}.log"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
  --python "$(cygpath -w "$ROOT/Art/Blender/build_landcruiser.py")" -- --version "$VERSION" --views "$VIEWS" --samples "$SAMPLES" > "$LOG" 2>&1
grep -E 'LC_MODEL_OK|LC_COUNTS|LC_RENDER_OK' "$LOG"

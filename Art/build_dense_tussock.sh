#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$ROOT/Art/Blender/build_dense_tussock.py" > "$ROOT/Saved/Logs/dense_tussock_blender.log" 2>&1
grep DENSE_TUSSOCK_BUILT "$ROOT/Saved/Logs/dense_tussock_blender.log"

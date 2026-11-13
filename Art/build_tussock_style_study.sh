#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$ROOT/Art/Blender/build_tussock_style_study.py" -- "${1:-07}" "${2:-all}" > "$ROOT/Saved/Logs/tussock_style_study.log" 2>&1
grep TUSSOCK_STYLE_STUDY_SAVED "$ROOT/Saved/Logs/tussock_style_study.log"

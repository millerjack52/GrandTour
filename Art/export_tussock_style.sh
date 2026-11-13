#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python "$ROOT/Art/Blender/export_tussock_style.py" > "$ROOT/Saved/Logs/tussock_style_export.log" 2>&1
grep TUSSOCK_STYLE_EXPORT_OK "$ROOT/Saved/Logs/tussock_style_export.log"

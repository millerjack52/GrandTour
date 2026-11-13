#!/usr/bin/env bash
# One-call editor build: refuses while the editor runs (Live Coding blocks UBT), runs UBT, prints only
# errors, warnings from project code and the result line.   bash Art/build.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if tasklist //FI "IMAGENAME eq UnrealEditor.exe" 2>/dev/null | grep -qi unrealeditor; then
  echo "BUILD BLOCKED: UnrealEditor.exe is running; close the editor first"; exit 2
fi
BAT="$(cygpath -w "/c/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat")"
PROJ="$(cygpath -w "$ROOT/GrandTour.uproject")"
OUT="$ROOT/Saved/Logs/build_last.txt"
mkdir -p "$ROOT/Saved/Logs"
start=$(date +%s)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$ROOT/Art/build_guarded.ps1")" > "$OUT" 2>&1
code=$?
secs=$(( $(date +%s) - start ))
grep -E "error|Error" "$OUT" | grep -v "0 error" | head -20
grep -E "warning" "$OUT" | grep "Source\\\\GrandTour\|Source/GrandTour" | head -10
tail -n 3 "$OUT" | cut -c1-200
echo "== build exit $code in ${secs}s (full output: Saved/Logs/build_last.txt)"
exit $code

#!/usr/bin/env bash
set -eu
if tasklist //FO CSV 2>/dev/null | grep -qiE 'UnrealEditor|GrandTour.exe|FarCry'; then
  echo 'ROAD_BENCHMARK blocked: an editor or game is running'; exit 2
fi
cmd //c "$(cygpath -w /c/GrandTour/Art/setup_road_benchmark.bat)" < /dev/null

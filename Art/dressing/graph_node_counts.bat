@echo off
setlocal
rem Stage B step 6 (docs/LandscapeMigrationManifest.md 9.B.6): READ-ONLY node-settings class counts of the 6 biome
rem graphs on GrandTour -> docs\landscape_migration\graph_nodes_<tag>.json (tag default: target).
rem Compare with the source run (see graph_node_counts.py) using:
rem   python Art\dressing\graph_node_counts.py diff docs\landscape_migration\graph_nodes_source.json docs\landscape_migration\graph_nodes_target.json
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set TAG=%~1
if "%TAG%"=="" set TAG=target
set GT_REPORT=%ROOT%\docs\landscape_migration\graph_nodes_%TAG%.json
echo Close the Unreal editor first.
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0graph_node_counts.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\graph_node_counts_%TAG%.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"GRAPH_NODE_COUNTS" "%ROOT%\Saved\Logs\graph_node_counts_%TAG%.log"
echo Done (Unreal exit code %RC%). Report: %GT_REPORT%
if "%GT_NOPAUSE%"=="" pause

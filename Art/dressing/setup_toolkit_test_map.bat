@echo off
setlocal
rem Stage C step 2 (docs/LandscapeMigrationManifest.md 9.C.2): build the toolkit test map
rem /Game/GrandTour/Test/L_OWToolkitTest (landscape, lighting, RVT volume, 6 biome PCG volumes, 3 roads, cliff wall).
rem   setup_toolkit_test_map.bat [overwrite]
rem overwrite -> delete and rebuild an existing map (env GT_TOOLKIT_OVERWRITE=1; -Script= drops script arguments).
rem Then run paint_road_verge.bat and tick_harness.ps1. Report: setup_toolkit_test_map_report.json next to this file.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_TOOLKIT_OVERWRITE=
if /I "%~1"=="overwrite" set GT_TOOLKIT_OVERWRITE=1
echo Close the Unreal editor first. Overwrite=%GT_TOOLKIT_OVERWRITE%
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0setup_toolkit_test_map.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\setup_toolkit_test_map.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"SETUP_TOOLKIT_TEST_MAP" /C:"OWToolkitSetup report" "%ROOT%\Saved\Logs\setup_toolkit_test_map.log"
echo Done (Unreal exit code %RC%). Report: %~dp0setup_toolkit_test_map_report.json
if "%GT_NOPAUSE%"=="" pause

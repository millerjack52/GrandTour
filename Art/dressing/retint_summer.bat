@echo off
setlocal
rem Leg dressing LD8a step 2 (docs/LEG_DRESSING_PLAN.md LD8a): the GT graphs' summer leaf copies. Close the editor first.
rem   retint_summer.bat          READ-ONLY inventory: every material the PCG_GT_* graphs spawn, its parent, its vector
rem                              params and their hue -> docs\landscape_migration\ld8_warm_materials.json
rem   retint_summer.bat apply    the summer copies MI_GT_Leaf_*_Summer in /Game/GrandTour/Dressing/Materials (the palette
rem                              table lives in retint_summer.py), Art\dressing\retint_summer_map.json for the commandlet,
rem                              report docs\landscape_migration\ld8_retint_summer.json. Then: create_biome_pcg.bat GT,
rem                              setup_dress_hide.bat, the tick harness (docs\LandscapeToolkit.md, leg dressing).
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_RETINT_MODE=inventory
if /I "%~1"=="apply" set GT_RETINT_MODE=apply
echo Close the Unreal editor first. Mode=%GT_RETINT_MODE%
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0retint_summer.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\retint_summer_%GT_RETINT_MODE%.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"RETINT_SUMMER" "%ROOT%\Saved\Logs\retint_summer_%GT_RETINT_MODE%.log"
echo Done (Unreal exit code %RC%).
if "%GT_NOPAUSE%"=="" pause

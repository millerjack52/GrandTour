@echo off
setlocal
rem Leg dressing LD6 (docs/LEG_DRESSING_PLAN.md LD6): dress The Hide (L_Leg03) headless - RebuildLandscape through the map's
rem terrain builder, the RVT on the landscape and an RVT volume over it, the exclusion rebuilt from DA_Terrain_Hide, five
rem GTBiome.* PCG volumes on PCG_GT_*, save. Rerunnable (it replaces its own GTHIDE_* actors by label).
rem   setup_dress_hide.bat            keep DA_Terrain_Hide as it is (it must carry biome rules)
rem   setup_dress_hide.bat pushspec   rewrite DA_Terrain_Hide from the C++ default first (the owner's edits are lost)
rem Then generate (the editor window shows while it runs):
rem   set GT_TICK_MAP=L_Leg03
rem   powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\tick_harness.ps1
rem     -Task C:\GrandTour\Art\dressing\tick_generate_only.py -Map /Game/GrandTour/Legs/L_Leg03
rem Rerun the tick harness after any RebuildLandscape. Report: docs\landscape_migration\ld6_hide_setup.json.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_PUSH_SPEC=
if /I "%~1"=="pushspec" set GT_PUSH_SPEC=1
echo Close the Unreal editor first. Push spec=%GT_PUSH_SPEC%
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0setup_dress_hide.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\setup_dress_hide.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"SETUP_DRESS_HIDE" /C:"BuildLegLandscape" "%ROOT%\Saved\Logs\setup_dress_hide.log"
echo Done (Unreal exit code %RC%). Report: %ROOT%\docs\landscape_migration\ld6_hide_setup.json
if "%GT_NOPAUSE%"=="" pause

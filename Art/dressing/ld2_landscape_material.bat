@echo off
setlocal
rem Leg dressing LD2 (docs/LEG_DRESSING_PLAN.md): rebuild M_GT_Landscape alone - the six surface rows as before plus the
rem biome rows, the OW grass output and the RVT output - through Art/Unreal/setup_m6_hide.py with GT_M6_STEP=material.
rem No map is loaded or rebuilt. Report: docs\landscape_migration\ld2_material.json (gate on its "ok").
rem Headless under NullRHI: no HLSL is compiled here; the real compile check is a -game run (Art\proving_shots.bat).
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_M6_STEP=material
set GT_M6_REPORT=%ROOT%\docs\landscape_migration\ld2_material.json
if exist "%GT_M6_REPORT%" del "%GT_M6_REPORT%"
echo Close the Unreal editor first. M_GT_Landscape only (GT_M6_STEP=%GT_M6_STEP%).
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%ROOT%\Art\Unreal\setup_m6_hide.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\ld2_landscape_material.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"SETUP_M6_HIDE" /C:"Error" "%ROOT%\Saved\Logs\ld2_landscape_material.log"
echo Done (Unreal exit code %RC%). Report: %GT_M6_REPORT%
if "%GT_NOPAUSE%"=="" pause

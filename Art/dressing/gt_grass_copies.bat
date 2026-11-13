@echo off
setlocal
rem Leg dressing LD8b (docs/LEG_DRESSING_PLAN.md): the GrandTour copies of the 10 OW grass types, LGT_GT_* in
rem /Game/GrandTour/Dressing/Grass (no dynamic shadow, contact shadow, no distance field lighting on every variety). Then
rem Art\dressing\ld2_landscape_material.bat points M_GT_Landscape's grass output at them. Close the editor first.
rem Report: docs\landscape_migration\ld8b_grass_copies.json.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0gt_grass_copies.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\gt_grass_copies.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"GT_GRASS_COPIES" "%ROOT%\Saved\Logs\gt_grass_copies.log"
echo Done (Unreal exit code %RC%).
if "%GT_NOPAUSE%"=="" pause

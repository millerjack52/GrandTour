@echo off
setlocal
rem Leg dressing LD4 step 6 (docs/LEG_DRESSING_PLAN.md): build the scratch map /Game/GrandTour/Test/L_GTDressScratch
rem (the Proving spec plus a test palette, the exclusion actor, five GTBiome.* PCG volumes on PCG_GT_*). Never touches
rem L_OWToolkitTest.   setup_gt_dress_scratch.bat [overwrite]
rem overwrite -> empty and rebuild an existing map (env GT_DRESS_OVERWRITE=1; -Script= drops script arguments).
rem Then generate: powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\tick_harness.ps1
rem   -Task C:\GrandTour\Art\dressing\tick_generate_only.py -Map /Game/GrandTour/Test/L_GTDressScratch
rem Report: docs\landscape_migration\ld4_scratch_setup.json.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_DRESS_OVERWRITE=
if /I "%~1"=="overwrite" set GT_DRESS_OVERWRITE=1
echo Close the Unreal editor first. Overwrite=%GT_DRESS_OVERWRITE%
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0setup_gt_dress_scratch.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\setup_gt_dress_scratch.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"SETUP_GT_DRESS_SCRATCH" /C:"BuildLegLandscape" "%ROOT%\Saved\Logs\setup_gt_dress_scratch.log"
echo Done (Unreal exit code %RC%). Report: %ROOT%\docs\landscape_migration\ld4_scratch_setup.json
if "%GT_NOPAUSE%"=="" pause

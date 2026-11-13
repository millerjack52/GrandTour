@echo off
setlocal
rem Leg dressing LD5 (docs/LEG_DRESSING_PLAN.md): build the vegetation physics test map /Game/GrandTour/Test/L_VegTest
rem (a flat floor, a brush patch, a sapling row, a young-tree row and a mature tree as tagged ISMs of the real meshes on
rem a GTBiome.Test actor). Then run Art\veg_test.bat.   setup_veg_test.bat [overwrite]
rem overwrite -> empty and rebuild an existing map (env GT_VEG_OVERWRITE=1; -Script= drops script arguments).
rem Report: docs\landscape_migration\ld5_veg_test_setup.json.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_VEG_OVERWRITE=
if /I "%~1"=="overwrite" set GT_VEG_OVERWRITE=1
echo Close the Unreal editor first. Overwrite=%GT_VEG_OVERWRITE%
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0setup_veg_test.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\setup_veg_test.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"SETUP_VEG_TEST" "%ROOT%\Saved\Logs\setup_veg_test.log"
echo Done (Unreal exit code %RC%). Report: %ROOT%\docs\landscape_migration\ld5_veg_test_setup.json
if "%GT_NOPAUSE%"=="" pause

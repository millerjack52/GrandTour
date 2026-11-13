@echo off
setlocal
rem Stage B step 4 (docs/LandscapeMigrationManifest.md 9.B.4): (re)generate the 6 biome PCG graphs
rem PCG_OW{Forest,Meadow,Scree,Road,Cliff,Alpine} in /Game/OWGame/Dev/DressingLab from the C++ baselines
rem (GrandTourEditor OWCreateBiomePCGCommandlet, river code stripped). A rerun stomps any live tuning back to the
rem baselines: run tune_meadow_look.bat afterwards.
rem   create_biome_pcg.bat GT  -> leg dressing LD4: the GrandTour variants PCG_GT_Forest/Meadow/Scree/Alpine/Brush in
rem   /Game/GrandTour/Dressing/PCG instead (the OW graphs untouched; never run tune_meadow_look on them), report
rem   docs\landscape_migration\ld4_gt_graphs.json.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set VARIANT=
set LOGNAME=create_biome_pcg
if /I "%~1"=="GT" set VARIANT=-Variant=GT
if /I "%~1"=="GT" set LOGNAME=create_biome_pcg_gt
rem   create_biome_pcg.bat GT hism -> LD7 cut step 1 A/B only: the GT soft classes on HISM (-GTSoftHISM).
if /I "%~2"=="hism" set VARIANT=%VARIANT% -GTSoftHISM
echo Close the Unreal editor first. %VARIANT%
%UE% "%ROOT%\GrandTour.uproject" -run=OWCreateBiomePCG %VARIANT% -Unattended -NullRHI -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\%LOGNAME%.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"LogOWCreateBiomePCG" "%ROOT%\Saved\Logs\%LOGNAME%.log"
echo Done (Unreal exit code %RC%). Log: %ROOT%\Saved\Logs\%LOGNAME%.log
if "%GT_NOPAUSE%"=="" pause

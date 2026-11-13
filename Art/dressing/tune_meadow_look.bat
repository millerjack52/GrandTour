@echo off
setlocal
rem Stage B step 5 (docs/LandscapeMigrationManifest.md 9.B.5): apply the live look/perf KNOBS of
rem tune_meadow_look.py to the OW LGTs and the PCG_OWMeadow / PCG_OWForest / PCG_OWRoad graphs and save them.
rem Run after every create_biome_pcg.bat (a regen stomps the tuning back to the C++ baselines).
rem Headless no map is loaded, so the Generate step is skipped. Report: tune_meadow_look_report.json here.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
echo Close the Unreal editor first.
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0tune_meadow_look.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\tune_meadow_look.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"MEADOWTUNE" "%ROOT%\Saved\Logs\tune_meadow_look.log"
echo Done (Unreal exit code %RC%). Report: %~dp0tune_meadow_look_report.json
if "%GT_NOPAUSE%"=="" pause

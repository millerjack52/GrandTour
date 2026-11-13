@echo off
setlocal
rem Leg dressing LD4 step 1 (docs/LEG_DRESSING_PLAN.md): READ-ONLY record of the tree variants' geometry, materials and
rem collision -> docs\landscape_migration\ld4_variants_<tag>.json (tag default: now).
rem   ld4_variant_geometry.bat before      (then run OWCreateTreeVariants)
rem   ld4_variant_geometry.bat after
rem   python Art\dressing\ld4_variant_geometry.py diff docs\landscape_migration\ld4_variants_before.json docs\landscape_migration\ld4_variants_after.json
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set TAG=%~1
if "%TAG%"=="" set TAG=now
set GT_REPORT=%ROOT%\docs\landscape_migration\ld4_variants_%TAG%.json
echo Close the Unreal editor first.
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0ld4_variant_geometry.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\ld4_variant_geometry_%TAG%.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"LD4_VARIANT_GEOMETRY" "%ROOT%\Saved\Logs\ld4_variant_geometry_%TAG%.log"
echo Done (Unreal exit code %RC%). Report: %GT_REPORT%
if "%GT_NOPAUSE%"=="" pause

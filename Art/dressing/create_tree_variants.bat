@echo off
setlocal
rem (Re)generate the 25 painterly tree variants in /Game/OWGame/Dev/DressingLab/Trees from the vendor Kasyanik trees
rem (GrandTourEditor OWCreateTreeVariantsCommandlet). Leg dressing LD4 (docs/LEG_DRESSING_PLAN.md): each tree, dead
rem tree and stump gets one trunk capsule, bushes none, all UseSimpleAsComplex; the check is the "LD4 capsule" lines
rem and docs\landscape_migration\ld4_variant_capsules.json. Geometry guard: ld4_variant_geometry.bat before / after.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
echo Close the Unreal editor first.
%UE% "%ROOT%\GrandTour.uproject" -run=OWCreateTreeVariants -Unattended -NullRHI -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\create_tree_variants.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"LD4 capsule" /C:"OWCreateTreeVariants done" /C:"Error:" "%ROOT%\Saved\Logs\create_tree_variants.log"
echo Done (Unreal exit code %RC%). Log: %ROOT%\Saved\Logs\create_tree_variants.log
if "%GT_NOPAUSE%"=="" pause

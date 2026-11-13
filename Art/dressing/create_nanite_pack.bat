@echo off
setlocal
rem Leg dressing LD7 cut step 1 (docs/LEG_DRESSING_PLAN.md LD7): the Nanite passthrough copies of the soft-class pack meshes
rem (SM_BirchBush_01..05_Summer, SM_CoverPlant_01..04_Summer) into /Game/GrandTour/Dressing/Nanite/SM_GTN_<name>: the vendor
rem meshes unchanged with Nanite on (Voxelize), made by OWCreateTreeVariants -GTNanitePack (no tree variant is touched).
rem The GT graphs (create_biome_pcg.bat GT) and L_VegTest (setup_veg_test.bat overwrite) use them. Check: the
rem "LD7 nanite copy" lines.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
echo Close the Unreal editor first.
%UE% "%ROOT%\GrandTour.uproject" -run=OWCreateTreeVariants -GTNanitePack -Unattended -NullRHI -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\create_nanite_pack.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"LD7 nanite" /C:"Error:" "%ROOT%\Saved\Logs\create_nanite_pack.log"
echo Done (Unreal exit code %RC%). Log: %ROOT%\Saved\Logs\create_nanite_pack.log
if "%GT_NOPAUSE%"=="" pause

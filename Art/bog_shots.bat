@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo The bog half of hide_shots.bat only (-GTShotsFrom=12): the leg's own pictures 1-11 are skipped and the car is put on
echo the route 10 m before the bog's Mud section, settled, and the run starts at step 12. Seventeen pictures into
echo Saved\Screenshots\M6: the bog from 40 m above after the crawl with M_GT_Mud's diagnostic ramp on
echo (hide_12_mud_diag), four of the rut band on foot (13-16, Art\tools\sample_rut_low.ps1), two of the mud patch
echo box's border (17-18, Art\tools\sample_border.ps1), one straight down from 3 m over a rut for the tyre's tread
echo (19, Art\tools\sample_tread.ps1), one from beside a rut along the ridge line (20, the same sampler's sidebox)
echo and one of the water standing in the ruts (21, the same sampler's wetbox), then the ford's three (22-24, water
echo stage W1, plus the motion probe's four; Art\tools\sample_ford.ps1 - Art\ford_shots.bat takes those alone).
echo The log is Saved\Logs\hide_shots.log,
echo the same file the full run writes, so the samplers find their box lines with no argument. Use hide_shots.bat
echo when the leg's other pictures matter.
rem Look stage L2 (VEHICLE_BUILD_SYSTEM 56): any arguments go to the game, e.g. -GTLook=0 -GTLookKuwahara=1 -GTLookDebug=2
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=hide_shots.log -GTHideShots -GTShotsFrom=12 -GTNoLoad -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud %*
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\hide_shots.log"
pause

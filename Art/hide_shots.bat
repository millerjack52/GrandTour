@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Thirty-two off-screen pictures of The Hide (L_Leg03 after setup_m6_hide) into Saved\Screenshots\M6: the valley from the
echo start, the climb, the dell with the bear, the stream crossing, an overview, the car sunk in the bog, the bog from
echo 70 m above, the wheels, the rally road, the track, the bog from 40 m above after the drive with M_GT_Mud's
echo diagnostic ramp on (hide_12_mud_diag: red the mud height, green the ground's Z, blue the tracks; judged by pixel),
echo four of the rut band on foot (13-16, Art\tools\sample_rut_low.ps1), two of the mud patch box's border
echo (17-18, near and from 40 m, Art\tools\sample_border.ps1), one straight down from 3 m over a rut for the
echo tyre's tread (19, Art\tools\sample_tread.ps1), one from beside a rut, 1.5 m up and 2 m to its side, along the
echo ridge line (20, stage I, Art\tools\sample_rut_low.ps1's sidebox) and one of the water standing in the ruts with
echo the table lifted by a wetness of 1 (21, stage G, hide_13's framing, the same sampler's wetbox), and three of the
echo ford (22-24, water stage W1: the crossing from the upstream bank, the car crossing it side on, the car parked in
echo it with the water raised 70 cm; Art\tools\sample_ford.ps1, or Art\ford_shots.bat for those alone), and the
echo motion probe's four (25-26, the W1 follow-up: two pictures half a second apart with the flow running and two
echo more with gt.Water.FlowScale 0, which the same sampler frame-diffs), WS2's wake pair and rain (27-28) and W4's
echo shallow edge from the near bank (29, hide_29_ford_shallow: the colour and the opacity where the bed shows through).
rem Look stage L2 (VEHICLE_BUILD_SYSTEM 56): any arguments go to the game, e.g. -GTLook=0 -GTLookKuwahara=1 -GTLookDebug=2
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=hide_shots.log -GTHideShots -GTNoLoad -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud %*
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\hide_shots.log"
pause

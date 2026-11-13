@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo The ford half of hide_shots.bat only (-GTShotsFrom=22, docs\WATER_PLAN.md stages W1 to W4): the leg's own
echo pictures and the bog's are skipped and the car is put on the route 3 m before the Ford section, settled, and the
echo run starts at step 22. Twelve pictures into Saved\Screenshots\M6: the crossing from the upstream bank with no car
echo in the water and a ring dropped on it (hide_22_ford_bank), the car crossing at 20 km/h seen side-on from the
echo downstream bank with a line logged ahead of its bow (hide_23_ford_cross), the car parked in it with the water
echo raised 70 cm (hide_24_ford_deep), the motion probe's two pairs (hide_25_ford_flow_a and _b half a second apart
echo with the current and the wind running, hide_26_ford_still_a and _b with gt.Water.FlowScale 0 and gt.Water.Wind
echo 0), WS2's wake pair a second apart after the car has crossed (hide_27_ford_wake_a and _b), the rain on the
echo water at intensity 1 (hide_28_ford_rain) and W4's shallow edge from the near bank at eye height, where the bed
echo still shows through the water (hide_29_ford_shallow, two boxes: edge and shallow) and, since water stage R1, a
echo rock in the ford from the near bank at eye height (hide_31_ford_rock, two boxes: the ring round the nearest
echo surface-breaking rock's waterline and the same ring of open water beside it). The runner also logs a GTWATERSTATS
echo line at the end of every step - frame ms, the field's step ms, sub-steps asked against run, clamps and the
echo simulated time they cost - and the sampler voids any picture whose step clamped.
echo The runner logs a fordbox line per box (the water, the far bank's
echo waterline, the bow ahead of the car) and a fordline per crest count, and the sampler Art\tools\sample_ford.ps1 counts them.
echo The log is Saved\Logs\hide_shots.log, the same file the full run writes, so the sampler finds its box lines with
echo no argument. Use hide_shots.bat when the leg's other pictures matter.
rem Look stage L2 (VEHICLE_BUILD_SYSTEM 56): any arguments go to the game, e.g. -GTLook=0 -GTLookKuwahara=1 -GTLookDebug=2
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=hide_shots.log -GTHideShots -GTShotsFrom=22 -GTNoLoad -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Water.M_GT_Water %*
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\hide_shots.log"
pause

@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Look stage L6 (docs/LOOK_PLAN.md L6, VEHICLE_BUILD_SYSTEM 57): the terrain dressing in the runtime painterly surface
echo M_GT_Painterly, on The Hide (L_Leg03) with the bog run's pattern (-GTShotsFrom=40): the leg's own pictures are
echo skipped, the car is put on the route 10 m before the bog and settled, then three objects are shot from 7 m at a
echo 25 degree field of view: the largest track stone within 20 m of the route at 1322 m (step 40), the rally post
echo nearest the route at 640 m (41) and the ford rock standing highest over its water (42). Five pictures each into
echo Saved\Screenshots\M6, the camera held: dress_^<kind^>_off (gt.Look.Surface 0), _on (1), _on_base and _off_base
echo (the same under gt.Look.Debug 1, the band pass's BaseColor view: the compose check divides the look by it) and
echo _plain (the MI_Env_* the dressing wore before L6 put back on the component: the switch's 0 against the real thing).
echo The L2 layer is on in every picture. The runner logs each object's box (borderbox dress_^<kind^>/^<kind^>, the middle
echo 60 %% of its visible surface on screen); Art\tools\sample_bands.ps1 -Dressing reads them. The log is
echo Saved\Logs\hide_shots.log, the same file the full run writes. Run Art\setup_look_l6.bat first.
rem Any arguments go to the game, e.g. -GTLookKuwahara=1
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=hide_shots.log -GTHideShots -GTShotsFrom=40 -GTNoLoad -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Painterly.M_GT_Painterly %*
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\hide_shots.log"
pause

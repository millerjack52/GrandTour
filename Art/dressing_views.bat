@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Leg dressing LD7 (docs/LEG_DRESSING_PLAN.md LD7 "Pictures"): four views of The Hide's biome dressing with the sky run's
echo camera (-GTShotsFrom=53): view_forest (inside the forest, 1.7 m up, looking away from the road), view_thicket (LD8a: from 15 m off the
echo route into the nearest Thicket-dominant ground), view_hilltop (on the highest scree or alpine point, looking
echo toward the route) and view_ford (the ford from the track 25 m past it), each in Clear with gt.Look.Dressing 1 and 0:
echo 8 pictures view_^<name^>_^<on^|dress0^> into Saved\Screenshots\M6. Art\sky_shots.bat runs them after its own 36.
echo The log is Saved\Logs\hide_shots.log. Run Art\dressing\setup_dress_hide.bat and the tick harness first.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=hide_shots.log -GTHideShots -GTShotsFrom=53 -GTNoLoad %*
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\hide_shots.log"
pause

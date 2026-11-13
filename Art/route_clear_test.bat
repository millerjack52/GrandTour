@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless route clearance test on L_Leg03 (leg dressing LD7, docs/LEG_DRESSING_PLAN.md): every 2 m along the route and
echo the alt routes a 3 x 4 x 2 m box swept to the next station hits no GTVeg.Solid instance and holds no soft instance of
echo the vegetation hash; no dressing within 5 m of the start, the checkpoints, the zone or an interactable. Run
echo Art\dressing\setup_dress_hide.bat and the tick harness first. Close the Unreal editor first.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -NullRHI -unattended -nopause -nosplash -nosound -log=route_clear_test.log -GTRouteClearTest -GTNoLoad
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\route_clear_test.log"
pause

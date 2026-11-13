@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Look stage L3 (docs/LOOK_PLAN.md L3, VEHICLE_BUILD_SYSTEM 58): the sky, the haze and the foliage on The Hide (L_Leg03)
echo with the dressing run's pattern (-GTShotsFrom=50): the leg's own pictures are skipped, the car is parked on the
echo route at the rally posts (640 m) and settled, then three spots with the camera held: sky_s (6 m behind the car,
echo 1.6 m up, pitched up 15 degrees: the sky over the car and the ground, the lighting check), sky_r (hide_10_rally's
echo frame: the far ridge, the car 40 m ahead in it) and sky_c (the foliage clump nearest the car from 7 m at a 25
echo degree field of view). Each in Clear - all on, gt.Look.Sky 0, gt.Look.Haze 0, gt.Look.Foliage 0, all on again -
echo (sky_s adds gt.Look.Debug 6 with the sky on and off, sky_c the card's DabNormal 1) and in Overcast - all on, Sky 0,
echo Haze 0, Foliage 0 - the weather held by gt.Look.Weather: 30 pictures sky_^<s^|r^|c^>_^<weather^>_^<switch^> into
echo Saved\Screenshots\M6. The L2 layer and L6's surface are on in every picture. The runner logs the boxes (borderbox
echo sky_^<spot^>/^<box^>) and the weather per picture; Art\tools\sample_bands.ps1 -Sky reads them. The log is
echo Saved\Logs\hide_shots.log, the same file the full run writes. Run Art\setup_look_l3.bat first.
rem Any arguments go to the game, e.g. -GTLookKuwahara=1
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=hide_shots.log -GTHideShots -GTShotsFrom=50 -GTNoLoad %*
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\hide_shots.log"
pause

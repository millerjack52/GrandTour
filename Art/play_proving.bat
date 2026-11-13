@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo The Proving Ground (L_Proving), windowed 1600x900. Drive it. The console (~) takes GTGoto <station>: pad, forda,
echo fordb, bog, rally, track, climbs, climbs25, climbs35, slope (GTGoto list names them), and the water and weather test
echo cvars gt.Water.ExtraRiseCm, gt.Water.FlowScale, gt.Water.Wind, gt.Water.RutWater, gt.Water.RiverLagScale,
echo gt.Water.Stats and gt.Weather.Rain. The station names and the cvars are on screen for the first 15 seconds.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Proving -game -windowed -ResX=1600 -ResY=900 -nosplash -log=play_proving.log
echo.
echo Done. Log: %ROOT%\Saved\Logs\play_proving.log
pause

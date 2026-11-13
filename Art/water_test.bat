@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless water test on L_Leg03 (run setup_m6_hide first), water stages WS1 and WS2 of docs\WATER_PLAN.md: the
echo ford's simulated surface on its own and the sources that move it, and W5's river stage. Nine steps, about 4
echo minutes.
echo (1) the current - after sixty seconds the speed where the route crosses must read the section's 1.5 m/s within
echo 20 percent and the field's volume must hold (1 percent over ten seconds, 2 over twenty).
echo (2) WS2's bow and wake - the car crosses at 20 km/h: a crest over 5 cm within 1.5 m ahead of the hull, a trough
echo under -3 cm within 2 m behind, the volume back within 0.5 percent and the middle within 1 cm of the level ten
echo seconds after it has left. (3) WS2's standing crest - the car parked in the current for five seconds piles the
echo water over 2 cm against its upstream side. (4) the raise and the sponge - 70 cm carried into the field lands
echo where it was asked, and 70 cm put on the two ends alone must reach the middle within 5 cm inside twenty seconds
echo and then swing less than 5 cm peak to peak (WS1 swung 38 to 58 cm on the basin's seiche: WS2's absorbing ends
echo are what stop it). (5) the ring - still water, a 20 cm impulse over a 1 m disc: the front reaches 5 m in 2.1 s
echo plus or minus 0.5, the crest at 5 m is under half the crest at 1 m, the volume holds within 0.1 percent, the
echo bank across the flow sends a crest back and the sponge at the end does not. (6) WS2's wind - the roughness of
echo the middle 10 by 10 m between 0.5 and 2 cm with the wind on and under 0.2 with it off. (7) WS2's rain at 1.0 -
echo the same roughness between 1 and 4 cm with the volume held (drops are impulses, not water). (8) W5's river
echo stage with the lags scaled to a twentieth - rain 1.0 for nine seconds must leave the stage at 50.6 cm within 2,
echo the surface at the ford's middle must ride within 5 cm of base plus stage and swing under 5 cm peak to peak
echo while it rises, and rain 0 for thirty seconds must leave 18.6 cm within 2. (9) the solver's cost with every
echo source on and the mesh and texture sizes. Add "gpu" to render instead of NullRHI.
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Water.M_GT_Water
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game %RHI% -unattended -nopause -nosplash -nosound -log=water_test.log -GTWaterTest -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" /C:"AGTWaterSheet" /C:"Failed to compile" "%ROOT%\Saved\Logs\water_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\water_test.log
pause

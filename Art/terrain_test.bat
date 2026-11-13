@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud
echo Headless terrain test on L_Leg03 (run setup_m6_hide first): a landscape under the leg's actors, the surfaces where
echo the spec paints them (tarmac in the valley, dirt on the climb, mud in the stream bed), a road with real grades and
echo no walls, relief off it, and the car drives the first stretch flat out without leaving the road. Add "gpu" to render.
rem Leg dressing LD7: the biome dressing off (-GTLookDressing=0: hidden, no collision, the vegetation physics inert). Step 3
rem sends the car flat out off the rally bend into the scenery; with the dressing it rolls on the trees there and the
rem damaged car then fails the bog escape and the raised ford. The dressing has its own tests (route_clear, veg, biome).
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game %RHI% -unattended -nopause -nosplash -nosound -log=terrain_test.log -GTTerrainTest -GTNoLoad -GTLookDressing=0
echo.
findstr /C:"GTDRIVETEST" /C:"AGTRunGameMode:" /C:"Failed to compile" "%ROOT%\Saved\Logs\terrain_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\terrain_test.log
pause

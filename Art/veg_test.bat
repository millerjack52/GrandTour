@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
if /I "%~1"=="scratch" goto scratch
echo Headless vegetation physics test (docs/LEG_DRESSING_PLAN.md LD5) on L_VegTest (Art\dressing\setup_veg_test.bat):
echo the car held at speed into brush (40 km/h), saplings (8, 30), young trees (10, 45) and a mature tree (20); bends,
echo resist, snaps and the clean-up against the plan's bands. Add "gpu" to render off-screen and also time the frame
echo over the brush with gt.Look.Dressing 1 and 0; "scratch" drives 100 m through L_GTDressScratch's densest thicket.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_VegTest -game %RHI% -unattended -nopause -nosplash -nosound -log=veg_test.log -GTVegTest -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" /C:"GTVEG" /C:"Failed to compile" "%ROOT%\Saved\Logs\veg_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\veg_test.log
pause
goto :eof
:scratch
echo Vegetation scratch probe (information only) on L_GTDressScratch: the soft instances indexed per class, the component
echo classes and the hash cells, then 100 m at 30 km/h through the densest soft vegetation clear of solid instances.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_GTDressScratch -game -NullRHI -unattended -nopause -nosplash -nosound -log=veg_scratch.log -GTVegTest -GTVegScratch -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" /C:"GTVEG" "%ROOT%\Saved\Logs\veg_scratch.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\veg_scratch.log
pause

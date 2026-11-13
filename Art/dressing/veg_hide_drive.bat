@echo off
setlocal
rem Leg dressing LD7 (docs/LEG_DRESSING_PLAN.md LD7 "Perf"): the car driven 100 m at a 30 km/h hold through the dense soft
rem vegetation nearest The Hide's route, gt.Look.Dressing 1 and then 0 over the same line; each pass's frame and GPU mean
rem and the vegetation subsystem's per-frame work (budget 0.3 ms). Information only. Close the Unreal editor first.
rem   veg_hide_drive.bat        on the GPU (-RenderOffScreen)
rem   veg_hide_drive.bat null   headless (no GPU numbers)
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set RHI=-RenderOffScreen
if /I "%~1"=="null" set RHI=-NullRHI
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg03 -game %RHI% -unattended -nopause -nosplash -nosound -log=veg_hide.log -GTVegTest -GTVegScratch -GTVegHide -GTNoLoad
findstr /C:"GTDRIVETEST" /C:"GTVEG" "%ROOT%\Saved\Logs\veg_hide.log"
if "%GT_NOPAUSE%"=="" pause

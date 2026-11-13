@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless winch test: take the hook, walk past the cable length (tether), hook a post, get in, reel the car
echo to it, snap the cable against a wall (winch damage), tear out a rotten post. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=winchtest.log -GTWinchTest
echo.
findstr /C:"GTDRIVETEST" /C:"UGTWinch" /C:"Failed to compile" "%ROOT%\Saved\Logs\winchtest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\winchtest.log
pause

@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless surface test: full throttle down L_TestTrack's tarmac, dirt, mud and snow lanes into the wall.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game -NullRHI -unattended -nopause -nosplash -nosound -log=surfacetest.log -GTSurfaceTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\surfacetest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\surfacetest.log
pause

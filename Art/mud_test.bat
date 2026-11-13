@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless mud-start test: sits on the mud lane for 4 s, then full throttle for 8 s.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game -NullRHI -unattended -nopause -nosplash -nosound -log=mudtest.log -GTMudTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\mudtest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\mudtest.log
pause

@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless rough-patch test: half throttle over the ridges, reports peak vertical g and pitch rate.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game -NullRHI -unattended -nopause -nosplash -nosound -log=roughtest.log -GTRoughTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\roughtest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\roughtest.log
pause

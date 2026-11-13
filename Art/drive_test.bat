@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless drive test: spawns the car on L_DriveTest, full throttle for 8 s, prints GTDRIVETEST lines.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game -NullRHI -unattended -nopause -nosplash -nosound -log=drivetest.log -GTDriveTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\drivetest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\drivetest.log
pause

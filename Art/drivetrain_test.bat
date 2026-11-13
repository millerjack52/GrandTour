@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless drivetrain test (driving feel stage 4) on L_DriveTest: open diffs on split friction versus locked, high versus low range on a 35 percent ramp, reverse, gear changes.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game -NullRHI -unattended -nopause -nosplash -nosound -log=drivetraintest.log -GTDrivetrainTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\drivetraintest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\drivetraintest.log
pause

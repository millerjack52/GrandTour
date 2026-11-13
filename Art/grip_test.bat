@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless grip test (driving feel stage 1): a tarmac pad and a dirt pad on L_DriveTest, the car run up to 65 km/h and held at full lock; prints the lateral g each surface holds.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game -NullRHI -unattended -nopause -nosplash -nosound -log=griptest.log -GTGripTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\griptest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\griptest.log
pause

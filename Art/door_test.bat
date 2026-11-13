@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless door test on L_DriveTest: four hinged doors swing open and shut, getting out opens the driver's door and
echo stands you behind it, look at a door to open or close it, look into the open doorway to get in (it shuts behind
echo you), a knocked-off door leaves the doorway open and the lift's repair hangs it back. Add "gpu" for two pictures
echo in Saved\Screenshots\Doors.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=door_test.log -GTDoorTest
echo.
findstr /C:"GTDRIVETEST" /C:"UGTBodyComponent:" /C:"Failed to compile" "%ROOT%\Saved\Logs\door_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\door_test.log
pause

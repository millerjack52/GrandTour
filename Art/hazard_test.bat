@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless hazard test: a weather front rolls over the parked car (storm pressure rises, exposure drains on foot,
echo glass and body take damage), then a radiation zone (engine damage, dash lamp, exposure on foot, an alloy cache
echo harvested inside). Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=hazard_test.log -GTHazardTest
echo.
findstr /C:"GTDRIVETEST" /C:"AGTWeatherFront" /C:"AGTRadiationZone" /C:"UGTWeatherSubsystem:" /C:"Failed to compile" "%ROOT%\Saved\Logs\hazard_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\hazard_test.log
pause

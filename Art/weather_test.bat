@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless weather test: clear to rain in 2 s, wetness rises, MPC_Weather and the tyres follow, drops fall and
echo none under a roof, exposure drains in the rain and not under cover, snow accumulates below zero, a parked front
echo lifts the rain by pressure. Add "gpu" to render off-screen: the occlusion capture is read back and M_GT_Environment
echo (puddles, occlusion) must compile.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=weather_test.log -GTWeatherTest -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Environment
echo.
findstr /C:"GTDRIVETEST" /C:"UGTWeatherSubsystem:" /C:"AGTRainEmitter:" /C:"Failed to compile" "%ROOT%\Saved\Logs\weather_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\weather_test.log
pause

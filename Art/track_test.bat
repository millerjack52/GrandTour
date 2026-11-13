@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless track-paint test: full throttle down the surface lanes for 16 s, then checks the rut grid.
echo Add "gpu" as the first argument to render off-screen and read the render target back as well.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game %RHI% -unattended -nopause -nosplash -nosound -log=tracktest.log -GTTrackTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\tracktest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\tracktest.log
pause

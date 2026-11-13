@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless body-state test: 16 s down the surface lanes; checks dirt by region, wetness and snow.
echo Add "gpu" as the first argument to render off-screen so the dirt/weather material must compile.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game %RHI% -unattended -nopause -nosplash -nosound -log=bodystatetest.log -GTBodyStateTest
echo.
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\bodystatetest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\bodystatetest.log
pause

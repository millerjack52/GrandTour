@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless spray and audio test: 16 s down the surface lanes; checks spray by lane and the synth's tyre colour.
echo Runs silent (-nosound); the synth block is rendered directly to check it has signal.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game %RHI% -unattended -nopause -nosplash -nosound -log=spraytest.log -GTSprayTest
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\spraytest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\spraytest.log
pause

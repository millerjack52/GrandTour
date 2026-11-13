@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless body test: drives into the wall from 35 m; checks panels, dent texture, front region death and panel detach.
echo Add "gpu" as the first argument to render off-screen so M_GT_Vehicle and M_GT_Glass must compile.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_TestTrack -game %RHI% -unattended -nopause -nosplash -nosound -log=bodytest.log -GTBodyTest
echo.
findstr /C:"GTDRIVETEST" /C:"UGTBodyComponent" /C:"Failed to compile" "%ROOT%\Saved\Logs\bodytest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\bodytest.log
pause

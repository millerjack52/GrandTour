@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless on-foot test: get out of the car, walk (head bob on and off), harvest a node, field-repair the
echo radiator, move items to the boot, drain exposure in a hazard, get back in. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=onfoottest.log -GTOnFootTest
echo.
findstr /C:"GTDRIVETEST" /C:"AGTPlayerCharacter:" /C:"AGTPlayerController:" /C:"Failed to compile" "%ROOT%\Saved\Logs\onfoottest.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\onfoottest.log
pause

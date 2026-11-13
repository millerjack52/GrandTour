@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless environment test: a flat profile of heat, dust and cold; 20 s flat out ramps heat and the filter clog
echo from performance to warning (lamps, temperature dial, torque loss) to slow engine damage; on foot the cold
echo drains the meter. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=env_test.log -GTEnvTest
echo.
findstr /C:"GTDRIVETEST" /C:"UGTEnvironmentComponent" /C:"AGTRunGameState:" /C:"Failed to compile" "%ROOT%\Saved\Logs\env_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\env_test.log
pause

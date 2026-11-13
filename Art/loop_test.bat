@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless loop test: starts on L_Leg01 (run setup_m3_leg and setup_m4_base first), clears the checkpoints, extracts
echo with 3 scrap and 1 wire in the boot, continues to L_Base (the haul and the save arrive, a heater is bought and
echo installed), drives out through the gate back to L_Leg01, where the loadout, the boot and the credits must have
echo carried. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Leg01 -game %RHI% -unattended -nopause -nosplash -nosound -log=loop_test.log -GTLoopTest -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" /C:"AGTRunGameMode:" /C:"AGTBaseGameMode:" /C:"UGTRunSubsystem:" /C:"Failed to compile" "%ROOT%\Saved\Logs\loop_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\loop_test.log
pause

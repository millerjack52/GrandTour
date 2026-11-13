@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless leg test: a runtime leg with two checkpoints and an extraction zone on L_DriveTest. The timer starts
echo on the first move, checkpoint 1 clears by driving through, extraction is refused early, checkpoint 2 and the
echo extraction hold finish the leg, the result (time, haul, rank) is recorded. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=leg_test.log -GTLegTest
echo.
findstr /C:"GTDRIVETEST" /C:"AGTRunGameState:" /C:"AGTRunGameMode:" /C:"UGTRunSubsystem:" /C:"Failed to compile" "%ROOT%\Saved\Logs\leg_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\leg_test.log
pause

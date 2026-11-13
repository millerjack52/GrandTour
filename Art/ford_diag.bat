@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Diagnostic only (2026-09-22, off every gate): L_Proving headless. Surveys forda/fordb (waterlines, 25 cm profiles, surface
echo changes, rows, rocks), then drives a dry 30 m on the pad and each ford from a standing start 15 m before the water to 15 m
echo past it at full throttle (base, gt.Water.Hull 0, gt.Water.Buoyancy 0, and a repeat of forda), with gt.Water.Diag on.
echo Tables: python Art/tools/ford_diag.py (reads Saved\Logs\ford_diag.log). About 5 minutes.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Proving -game -NullRHI -unattended -nopause -nosplash -nosound -log=ford_diag.log -GTFordDiag -GTNoLoad
echo.
findstr /C:"GTDRIVETEST_RESULT" /C:"GTFORDDIAG end" "%ROOT%\Saved\Logs\ford_diag.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\ford_diag.log
pause

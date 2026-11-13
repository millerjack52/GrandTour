@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless smoke test of The Proving Ground (L_Proving, run setup_m6_proving first): the map loads with its landscape,
echo the water sheets, the mud patch, the dressing's rocks, stones and posts and the winch posts the spec asks for; the car
echo spawns on the pad at rest; and GTGoto lands it at rest inside every station (the fords' water, the bog's patch, the
echo ramps' grades, the slope's cross slope). About 90 s.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Proving -game -NullRHI -unattended -nopause -nosplash -nosound -log=proving_test.log -GTProvingTest -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" /C:"AGTRunGameMode:" /C:"Failed to compile" "%ROOT%\Saved\Logs\proving_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\proving_test.log
pause

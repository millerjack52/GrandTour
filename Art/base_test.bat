@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless base test: the five stations spawned beside the car on L_DriveTest. Craft a radiator, install it (the old
echo one to the boot), repair for scrap, wash, sell wire, buy and install a heater (cold resistance), a crew upgrade refused
echo then bought, the briefing shows peaks, a coolant flush and a thermal blanket, and a save / load round trip.
echo Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=base_test.log -GTBaseTest
echo.
findstr /C:"GTDRIVETEST" /C:"AGTWorkbench:" /C:"AGTCarLift:" /C:"AGTCrewTent:" /C:"UGTPartSlotsComponent:" /C:"UGTRunSubsystem:" /C:"Failed to compile" "%ROOT%\Saved\Logs\base_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\base_test.log
pause

@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless M5 tour test on L_DriveTest with a runtime tour (no assets needed): the legs and missions resolve, the
echo rivals' draw is deterministic and bounded, a photograph leg refuses the zone until the picture is taken from range
echo (a second subject flees), an endurance leg over its limit is a did-not-finish, the tour ends with a table and an
echo ending that survive the save, and the briefing board starts a new tour. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=tour_test.log -GTTourTest -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" /C:"AGTRunGameMode:" /C:"AGTRunGameState:" /C:"AGTPhotoSubject:" /C:"UGTRunSubsystem:" /C:"AGTBriefingBoard:" /C:"Failed to compile" "%ROOT%\Saved\Logs\tour_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\tour_test.log
pause

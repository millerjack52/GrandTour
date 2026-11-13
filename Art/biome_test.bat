@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Headless biome test (docs/LEG_DRESSING_PLAN.md LD1 + LD3) on L_DriveTest: the no-biome hashes of the Hide and
echo Proving specs are unchanged; with the D2 palette the heights and layers 0-3 and 5 are byte-identical and the biome
echo layers share out the Scrub weight; the dressing exclusion boxes, the global wind, gt.Look.Dressing, no L3 cards.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game -NullRHI -unattended -nopause -nosplash -nosound -log=biome_test.log -GTBiomeTest -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\biome_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\biome_test.log
pause

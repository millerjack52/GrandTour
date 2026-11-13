@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless loot test: 200 rolls of the wreck table stay within their bounds and weights; a node with the
echo radiation cache table pays rare alloy into the bag. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_DriveTest -game %RHI% -unattended -nopause -nosplash -nosound -log=loot_test.log -GTLootTest
echo.
findstr /C:"GTDRIVETEST" /C:"AGTHarvestNode" /C:"Failed to compile" "%ROOT%\Saved\Logs\loot_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\loot_test.log
pause

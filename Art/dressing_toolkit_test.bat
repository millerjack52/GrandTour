@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set RHI=-NullRHI
if /I "%~1"=="gpu" set RHI=-RenderOffScreen
echo Headless OW landscape toolkit smoke test on L_OWToolkitTest (docs/LandscapeToolkit.md): 3 BP_OWRoad* roads with
echo a road bed component, landscape material MI_OWDressingLab_Style, exactly the 13 non-water layer infos painted,
echo and ISM instances saved on each of the 6 OWBiome.* PCG volumes. Add "gpu" to render off-screen.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Test/L_OWToolkitTest -game %RHI% -unattended -nopause -nosplash -nosound -log=dressing_toolkit_test.log -GTDressingTest
echo.
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\dressing_toolkit_test.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\dressing_toolkit_test.log
pause

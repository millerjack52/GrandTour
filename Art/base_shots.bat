@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Screenshots of L_Base rendered off-screen (run setup_m4_base first): two overviews, the yard at eye level and the
echo car lift screen, then all four doors open and the view into the driver's doorway, written to Saved\Screenshots\M4. The first run can take a few minutes while shaders compile.
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Base/L_Base -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=base_shots.log -GTBaseShots -GTNoLoad
echo.
findstr /C:"GTDRIVETEST" "%ROOT%\Saved\Logs\base_shots.log"
echo.
echo Done (exit code %ERRORLEVEL%). Pictures: %ROOT%\Saved\Screenshots\M4
pause

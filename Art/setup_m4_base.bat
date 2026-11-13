@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Writes the item, recipe and crew-upgrade assets and builds L_Base (lift, workbench,
echo trader, crew tent, briefing board, departure gate). Run setup_m1_track and setup_m3_leg before it.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m4_base.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m4_base.log
echo.
findstr /C:"SETUP_M4_BASE" /C:"Error" "%ROOT%\Saved\Logs\setup_m4_base.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m4_base.log
pause

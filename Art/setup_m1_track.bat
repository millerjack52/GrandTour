@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Creates the surface physical materials, the environment master material and L_TestTrack.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m1_track.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m1_track.log
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m1_track.log
pause

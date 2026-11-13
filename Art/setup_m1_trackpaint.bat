@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Creates RT_TrackPaint, MPC_TrackPaint and MF_TrackPaint and wires the ruts into M_GT_Environment.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m1_trackpaint.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m1_trackpaint.log
echo.
findstr /C:"SETUP_M1_TRACKPAINT" /C:"Failed to compile" "%ROOT%\Saved\Logs\setup_m1_trackpaint.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m1_trackpaint.log
pause

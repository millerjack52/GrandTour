@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Adds the mud patches' boxes (Patch0..3, PatchCount) to MPC_TrackPaint, which the
echo landscape material pushes its Mud and Bog layers back under, and builds M_GT_Mud (the mud mesh material: displaced
echo by a patch's field texture, a mud look over the ground by the tracks, MPC_Weather's wetness for the sheen, a
echo diagnostic height ramp). Run setup_m3_weather and setup_m1_trackpaint first; run setup_m6_hide after it.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m6_mud.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m6_mud.log
echo.
findstr /C:"SETUP_M6_MUD" /C:"Error" "%ROOT%\Saved\Logs\setup_m6_mud.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m6_mud.log
pause

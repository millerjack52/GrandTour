@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Builds M_GT_Landscape (a copy of the environment master with layer blends), the four
echo landscape layer infos, and gives L_Leg03 (The Hide) real ground: a generated landscape with the road carved along
echo the route and the leg's actors placed on it. Run setup_m1_track, setup_m3_weather, setup_m3_leg, setup_m5_legs and
echo setup_m6_mud (the mud patch boxes in MPC_TrackPaint for the landscape's depth offset under them) first.
echo Add "reset" to overwrite DA_Terrain_Hide with the C++ default (your edits to it are lost); without it the asset is kept.
set GT_RESET_SPEC=0
if /I "%~1"=="reset" set GT_RESET_SPEC=1
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m6_hide.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m6_hide.log
echo.
findstr /C:"SETUP_M6_HIDE" /C:"BuildLegLandscape" /C:"Error" "%ROOT%\Saved\Logs\setup_m6_hide.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m6_hide.log
pause

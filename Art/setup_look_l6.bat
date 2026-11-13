@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Look stage L6 (docs/LOOK_PLAN.md L6, VEHICLE_BUILD_SYSTEM 57): builds the runtime
echo painterly surface M_GT_Painterly in /Game/GrandTour/Materials (a fresh copy of M_GT_Environment with the painted
echo surface in front of MF_Weather and the Normal pin, behind a Surface scalar), MI_GT_Painterly_Stone/_Rock/_Post in
echo /Game/GrandTour/Materials/Painterly (each copying the plain instance its kind wore), imports the dab tile
echo Art\Textures\Painted\T_GT_DabTile_N.png (bash Art/make_dab_tile.sh) into /Game/GrandTour/Textures/Painted, and
echo re-dresses The Hide (L_Leg03) through its builder's RebuildDressing, then saves the level. Run it again after an
echo MF_Weather rebuild (setup_m3_weather) or a change to M_GT_Environment: the copy is made fresh every run.
echo NullRHI compiles no HLSL: the shaders compile on the next rendered run (Art\dressing_shots.bat).
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_look_l6.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_look_l6.log
echo.
findstr /C:"SETUP_LOOK_L6" /C:"Error" "%ROOT%\Saved\Logs\setup_look_l6.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_look_l6.log
pause

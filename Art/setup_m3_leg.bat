@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Writes the loot tables and DA_Leg_01, and builds L_Leg01 (the 1.2 km greybox leg:
echo roof, dirt, mud, checkpoints, extraction, radiation pocket with caches, nodes, wrecks, a weather front).
echo Run setup_m1_track and setup_m3_weather before it.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m3_leg.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m3_leg.log
echo.
findstr /C:"SETUP_M3_LEG" /C:"SETUP_M1_WEATHER" /C:"SETUP_M1_MASTERS" /C:"Error" "%ROOT%\Saved\Logs\setup_m3_leg.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m3_leg.log
pause

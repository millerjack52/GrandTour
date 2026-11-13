@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Writes DA_Leg_01..05 and DA_Tour_01, and builds the greybox legs L_Leg02..L_Leg05
echo (the river road, the hide with the bear, the pass, the salt). Run setup_m1_track, setup_m3_weather and setup_m3_leg before it.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m5_legs.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m5_legs.log
echo.
findstr /C:"SETUP_M5_LEGS" /C:"Error" "%ROOT%\Saved\Logs\setup_m5_legs.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m5_legs.log
pause

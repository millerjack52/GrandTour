@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Rebuilds MPC_Weather and MF_Weather (rain occlusion, puddles, CanPool), creates
echo RT_RainOcclusion, re-routes the masters, and writes the five weather state assets under /Game/GrandTour/Weather.
echo Run setup_m1_track and setup_m1_body before it.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m3_weather.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m3_weather.log
echo.
findstr /C:"SETUP_M3_WEATHER" /C:"SETUP_M1_WEATHER" /C:"SETUP_M1_MASTERS" /C:"Error" "%ROOT%\Saved\Logs\setup_m3_weather.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m3_weather.log
pause

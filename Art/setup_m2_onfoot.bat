@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Builds L_OnFootTest: floor, mud lane, cable bundles, a wreck, two winch posts, a hazard volume and a wall.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m2_onfoot.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m2_onfoot.log
echo.
findstr /C:"SETUP_M2_ONFOOT" "%ROOT%\Saved\Logs\setup_m2_onfoot.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m2_onfoot.log
pause

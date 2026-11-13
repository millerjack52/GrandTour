@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Copies the Epic mannequin (first-person arms) into Content\Characters,
echo writes the on-foot input assets, rewrites IMC_Driving with Exit and Reel, and writes the three tool assets.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m2_character.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m2_character.log
echo.
findstr /C:"SETUP_M2_CHARACTER" "%ROOT%\Saved\Logs\setup_m2_character.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m2_character.log
pause

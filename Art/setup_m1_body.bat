@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Creates M_GT_Vehicle (with MF_Dents) and M_GT_Glass for the car's body panels and windscreen.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m1_body.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m1_body.log
echo.
findstr /C:"SETUP_M1_BODY" "%ROOT%\Saved\Logs\setup_m1_body.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m1_body.log
echo The HLSL is only compiled by a GPU run: body_test.bat gpu reports "Failed to compile" if it is wrong.
pause

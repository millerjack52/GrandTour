@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Creates M_GT_Foliage and M_GT_Character and routes every master through MF_Weather.
echo Run after setup_m1_track, setup_m1_cockpit, setup_m1_weather and setup_m1_body.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m1_masters.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m1_masters.log
echo.
findstr /C:"SETUP_M1_MASTERS" "%ROOT%\Saved\Logs\setup_m1_masters.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m1_masters.log
echo Compile check: any *_test.bat gpu run, with -GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Foliage.M_GT_Foliage,/Game/GrandTour/Materials/M_GT_Character.M_GT_Character for the masters nothing wears yet.
pause

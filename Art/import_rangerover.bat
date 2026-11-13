@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first: this writes assets into Content\GrandTour\Vehicles\Bodies\RangeRover.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\import_rangerover.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=import_rangerover.log
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\import_rangerover.log
pause

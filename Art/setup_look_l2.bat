@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Look stage L2 (docs/LOOK_PLAN.md, VEHICLE_BUILD_SYSTEM 56): builds the post-process
echo band pass M_GT_PostLook and the anisotropic Kuwahara filter M_GT_PostKuwahara in /Game/GrandTour/Materials, with
echo MI_GT_PostLook and MI_GT_PostKuwahara in /Game/GrandTour/Materials/Look. UGTLookSubsystem puts them on every level
echo at run time (an unbound post-process volume per game world) and sets their numbers from the weather state.
echo NullRHI compiles no HLSL: the shaders compile on the next rendered run (Art\proving_shots.bat 4 is the short one).
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_look_l2.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_look_l2.log
echo.
findstr /C:"SETUP_LOOK_L2" /C:"Error" "%ROOT%\Saved\Logs\setup_look_l2.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_look_l2.log
pause

@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Look stage L3 (docs/LOOK_PLAN.md L3, VEHICLE_BUILD_SYSTEM 58): runs setup_look_l2.py
echo first (M_GT_PostLook with the L3 haze behind its Haze scalar), then builds the painted sky M_GT_Sky + MI_GT_Sky
echo (unlit, translucent Before DOF, no fog; UGTLookSubsystem puts it on a transient 10 km dome), the foliage card
echo M_GT_FoliageCard (a fresh copy of M_GT_Foliage, masked, the PLACEHOLDER blade fan) + MI_GT_FoliageCard_Scrub, and
echo re-dresses The Hide (L_Leg03) through its builder's RebuildDressing (the stones, rocks, posts and the new foliage
echo cards), then saves the level. Run it again after an MF_Weather rebuild or a change to M_GT_Foliage: the card is a
echo fresh copy every run. NullRHI compiles no HLSL: the shaders compile on the next rendered run (Art\sky_shots.bat).
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_look_l3.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_look_l3.log
echo.
findstr /C:"SETUP_LOOK_L3" /C:"SETUP_LOOK_L2" /C:"Error" "%ROOT%\Saved\Logs\setup_look_l3.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_look_l3.log
pause

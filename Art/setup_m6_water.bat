@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Builds the two water materials. M_GT_MudWater, the water standing in the ruts (docs/MUD_ONE_SURFACE_PLAN.md
echo stage G): a translucent sheet on a second grid over each mud patch, at the ground plus the section's WaterTableCm,
echo which reads the patch's own field texture and draws nothing where the mud stands above the table - so only the
echo ruts hold water and the surface follows the ground cell by cell. Run setup_m1_trackpaint first (RT_TrackPaint is
echo the linear default for the field parameter); run it before setup_m6_mud.bat and setup_m6_hide.bat.
echo And M_GT_Water, a ford's sheet (docs/WATER_PLAN.md stage W1): the same translucent blue-green look it always had
echo plus the flow parameters (FlowDir, FlowSpeed) AGTWaterSheet sets, and a procedural two-band sine ripple panned
echo along the current so the driver can see which way the water runs. Both are rebuilt from scratch every run.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m6_water.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m6_water.log
echo.
findstr /C:"SETUP_M6_WATER" /C:"Error" "%ROOT%\Saved\Logs\setup_m6_water.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m6_water.log
pause

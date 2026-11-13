@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Builds The Proving Ground (L_Proving): a 378 m landscape from DA_Terrain_Proving with a
echo 697 m loop off a tarmac skid pan - two fords, a bog, a rally stretch, a track, three ramps and a cross slope - plus the
echo water sheets and the winch posts. Run setup_m1_track, setup_m3_weather, setup_m6_textures, setup_m6_water, setup_m6_mud
echo and setup_m6_hide first (this reuses M_GT_Landscape and M_GT_Water; it does not rebuild them).
echo Add "reset" to overwrite DA_Terrain_Proving with the C++ default (your edits to it are lost); without it the asset is kept.
set GT_RESET_SPEC=0
if /I "%~1"=="reset" set GT_RESET_SPEC=1
set GT_ART_UNREAL=%~dp0Unreal
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m6_proving.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m6_proving.log
echo.
findstr /C:"SETUP_M6_PROVING" /C:"SETUP_M6_HIDE" /C:"BuildLegLandscape" /C:"Error" "%ROOT%\Saved\Logs\setup_m6_proving.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m6_proving.log
pause

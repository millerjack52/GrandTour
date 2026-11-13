@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo Close the Unreal editor first. Look stage L1 (docs/LOOK_PLAN.md, VEHICLE_BUILD_SYSTEM 55): imports every
echo GT Paint export in Art\Export\^<Asset^>\ (SM_^<Asset^>.fbx, T_GT_^<Asset^>_D.png, T_GT_^<Asset^>_M.png, T_GT_^<Asset^>_N.png) - the mesh into
echo /Game/GrandTour/Props/Painted, the bake into /Game/GrandTour/Textures/Painted - builds M_GT_Painted and the plain
echo grey M_GT_PaintedGrey in /Game/GrandTour/Materials, and gives each mesh its MI_GT_Painted_^<Asset^>. Bake and export
echo from the GT Paint panel in Blender first (bash Art/blender_test.sh makes TestCube, TestBox and TestCar).
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_look_l1.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_look_l1.log
echo.
findstr /C:"SETUP_LOOK_L1" /C:"Error" "%ROOT%\Saved\Logs\setup_look_l1.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_look_l1.log
pause

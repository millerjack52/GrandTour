@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
echo L_Proving's picture mode (RIVERBED S2, 2026-09-23, VEHICLE_BUILD_SYSTEM 52), rendered off screen at 1280x720. Step 1:
echo the car parked on forda's channel bank (the channel's floor past the ford's sheet, Mud before section 52), settled
echo on the handbrake, then a picture from each side at wheel height: proving_01_bank_left and proving_02_bank_right in
echo Saved\Screenshots\Proving. The log (Saved\Logs\proving_shots.log) carries each near wheel's tyre box, the drawn
echo tyre's lowest point and the ground line under its outer face in pixels; Art\tools\sample_wheels.ps1 reads them.
echo Then the control: the same car settled on a flat Dirt climb top and shot from its sunlit side (proving_03_flat_sunlit).
echo Step 2 (RIVERBED S3, VEHICLE_BUILD_SYSTEM 53): forda's pond from the forda station with the eye 5 m up, the owner's
echo picture 2 (proving_04_forda_basin); the log carries pairs of points either side of the placed box's flow-wise ends,
echo Art\tools\sample_basin.ps1 counts the water pixels on each side. Pass a step to start there: proving_shots.bat 2.
echo Step 3 (RIVERBED S4, VEHICLE_BUILD_SYSTEM 54): forda's ruts under the water from the entry bank before and after a
echo crossing at full throttle (proving_05_forda_ruts_before, proving_06_forda_ruts_after; Art\tools\sample_ford_ruts.ps1)
echo and the bed patch's box edge on the approach (proving_07_forda_box_edge; sample_border.ps1 -LogName proving_shots.log
echo -Folder Proving -Step 3 -Names proving_07_forda_box_edge).
echo Step 4 (LOOK L1, VEHICLE_BUILD_SYSTEM 55): the GT Paint props SM_TestBox and SM_TestCar beside the car parked on the
echo flat Dirt top, first in the plain grey M_GT_PaintedGrey (proving_08_painted_before), then in their MI_GT_Painted_^<Asset^>
echo (proving_09_painted_after); Art\tools\sample_tones.ps1 reads the boxes. Run bash Art/blender_test.sh and
echo Art\setup_look_l1.bat first. proving_shots.bat 4 takes these two alone.
set FROM=
if not "%~1"=="" set FROM=-GTShotsFrom=%~1
rem Look stage L2 (VEHICLE_BUILD_SYSTEM 56): the arguments after the step go to the game, e.g. proving_shots.bat 4 -GTLook=0
set EXTRA=
for /f "tokens=1,* delims= " %%a in ("%*") do set EXTRA=%%b
%UE% "%ROOT%\GrandTour.uproject" /Game/GrandTour/Legs/L_Proving -game -RenderOffScreen -unattended -nopause -nosplash -nosound -log=proving_shots.log -GTProvingShots -GTNoLoad %FROM% %EXTRA%
echo.
findstr /C:"GTDRIVETEST" /C:"Failed to compile" "%ROOT%\Saved\Logs\proving_shots.log"
echo.
echo Done (exit code %ERRORLEVEL%). Full log: %ROOT%\Saved\Logs\proving_shots.log
pause

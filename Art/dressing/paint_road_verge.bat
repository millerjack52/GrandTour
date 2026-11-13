@echo off
setlocal
rem Stage C step 3 (docs/LandscapeMigrationManifest.md 9.C.3): paint OW_RoadVerge along every BP_OWRoad* spline in
rem L_OWToolkitTest with the GrandTourEditor OWPaintRoadVerge commandlet, pump the edit-layer merge, verify by
rem read-back, save. The merge runs on the GPU: a commandlet gets a real RHI only with -AllowCommandletRendering
rem (leaving out -NullRHI is not enough; without it FApp::CanEverRender() is false and the merge never runs).
rem   paint_road_verge.bat [/Game/Map/Path]    (default /Game/GrandTour/Test/L_OWToolkitTest; -Map= is required)
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set MAP=%~1
if "%MAP%"=="" set MAP=/Game/GrandTour/Test/L_OWToolkitTest
echo Close the Unreal editor first. Map %MAP%
%UE% "%ROOT%\GrandTour.uproject" -run=OWPaintRoadVerge -Map=%MAP% -AllowCommandletRendering -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\paint_road_verge.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"LogOWPaintRoadVerge" "%ROOT%\Saved\Logs\paint_road_verge.log"
echo Done (Unreal exit code %RC%). Log: %ROOT%\Saved\Logs\paint_road_verge.log
if "%GT_NOPAUSE%"=="" pause

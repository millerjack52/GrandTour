@echo off
setlocal
rem Stage B audit of the ported OW landscape toolkit (docs/LandscapeMigrationManifest.md 9.B.3 / 9.B.7).
rem   audit_toolkit.bat [tag] [resave]
rem tag    -> report docs\landscape_migration\audit_<tag>.json and log Saved\Logs\audit_toolkit_<tag>.log
rem resave -> after the audit, compile + resave the 3 road BPs, only if all 3 show OWRoadBed with class
rem           /Script/GrandTour.OWRoadBedComponent (the CoreRedirect works). Otherwise read-only.
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..\..") do set ROOT=%%~fI
set GT_AUDIT_TAG=%~1
if "%GT_AUDIT_TAG%"=="" set GT_AUDIT_TAG=audit
set GT_AUDIT_RESAVE=
if /I "%~2"=="resave" set GT_AUDIT_RESAVE=1
echo Close the Unreal editor first. Audit tag %GT_AUDIT_TAG%, resave=%GT_AUDIT_RESAVE%
%UE% "%ROOT%\GrandTour.uproject" -run=PythonScript "-Script=%~dp0audit_toolkit.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%ROOT%\Saved\Logs\audit_toolkit_%GT_AUDIT_TAG%.log"
set RC=%ERRORLEVEL%
echo.
findstr /C:"AUDIT_TOOLKIT" "%ROOT%\Saved\Logs\audit_toolkit_%GT_AUDIT_TAG%.log"
echo Done (Unreal exit code %RC%). Report: %ROOT%\docs\landscape_migration\audit_%GT_AUDIT_TAG%.json
if "%GT_NOPAUSE%"=="" pause

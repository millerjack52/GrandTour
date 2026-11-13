@echo off
setlocal
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "%~dp0..\GrandTour.uproject" -run=PythonScript "-Script=%~dp0Unreal\setup_road_benchmark.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%~dp0..\Saved\Logs\setup_road_benchmark.log"
exit /b %ERRORLEVEL%

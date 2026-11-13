@echo off
setlocal
tasklist /FI "IMAGENAME eq UnrealEditor.exe" /NH | find /I "UnrealEditor.exe" >nul && exit /b 2
tasklist /FI "IMAGENAME eq UnrealEditor-Cmd.exe" /NH | find /I "UnrealEditor-Cmd.exe" >nul && exit /b 2
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "%~dp0..\GrandTour.uproject" -run=PythonScript "-Script=%~dp0Unreal\setup_grass_benchmark.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=%~dp0..\Saved\Logs\setup_grass_benchmark.log"
exit /b %ERRORLEVEL%

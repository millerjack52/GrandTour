@echo off
setlocal
set PYTHONIOENCODING=utf-8
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
echo Save rangerover.blend in Blender first: this reads the file on disk.
%BLENDER% -b --factory-startup "%~dp0rangerover.blend" --python "%~dp0Blender\export_rangerover.py" -- "%~dp0Export"
echo.
echo Done (exit code %ERRORLEVEL%). Output: %~dp0Export
pause

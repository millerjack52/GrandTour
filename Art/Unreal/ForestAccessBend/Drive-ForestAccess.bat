@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-ForestAccess.ps1" -PreviewOnly
if errorlevel 1 pause

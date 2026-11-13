@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Art\play_benmore_native.ps1"
if errorlevel 1 pause

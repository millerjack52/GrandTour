@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Art\play_bigmountain.ps1"
if errorlevel 1 pause

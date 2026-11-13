@echo off
start "GrandTour Mud Lab" "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0GrandTour.uproject" /Game/GrandTour/ArtTests/MudLab/L_MudLab -game -windowed -ResX=1440 -ResY=900 -GTNoLoad -NoSplash -ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1"

@echo off
start "" "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "C:\GrandTour\GrandTour.uproject" "/Game/GrandTour/ArtTests/FloraGroup/L_FloraGroup" -GTNoLoad -GTLookKuwahara=0 -GTLidarPerformance=0 -ExecCmds="gt.Look.Post 0,r.AntiAliasingMethod 4,r.ScreenPercentage 100,r.DistanceFieldAO 0,r.Lumen.DiffuseIndirect.Allow 0,r.Lumen.Reflections.Allow 0"

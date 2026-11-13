# Interactive entry point for the integrated Gaea level. The user drives.
$ErrorActionPreference='Stop'
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'Unreal is already running. Open L_Benmore_GaeaReview there, or close it before using this launcher.'}
$taskRoot=Split-Path $PSScriptRoot
$taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview','-game','-GTNoLoad','-GTLookKuwahara=0','-windowed','-ResX=1600','-ResY=900')
Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs

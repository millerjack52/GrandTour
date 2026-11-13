# Interactive entry point: the user drives.
$ErrorActionPreference='Stop'
& "$PSScriptRoot/wait_unreal_free.ps1" -MaxMinutes 0
if($LASTEXITCODE -ne 0){throw 'Unreal is already running; open L_BigMountain there or close it first.'}
$taskRoot=Split-Path $PSScriptRoot
$taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/BigMountain/L_BigMountain','-game','-GTNoLoad','-GTLookKuwahara=0','-windowed','-ResX=1600','-ResY=900')
Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs

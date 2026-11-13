param([switch]$Play)
$ErrorActionPreference='Stop'
& "$PSScriptRoot/wait_unreal_free.ps1" -MaxMinutes 0
if($LASTEXITCODE -ne 0){throw 'Unreal is already open. Load /Game/GrandTour/ArtTests/NativePlants/L_NativePlants there.'}
$taskRoot=Split-Path $PSScriptRoot
$taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/NativePlants/L_NativePlants','-GTNoLoad','-GTLookKuwahara=0')
if($Play){$taskArgs+=@('-game','-windowed','-ResX=1600','-ResY=900')}
# Explicitly interactive editor/game requested by the launcher user.
Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs

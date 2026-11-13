# Launch the first real-terrain road blockout with the existing driving pawn.
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$exe='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$launchArgs=@(('"'+$projectRoot+'\GrandTour.uproject"'),'/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive','-game','-windowed','-ResX=1600','-ResY=900','-GTNoLoad','-GTLook=0','-GTLookKuwahara=0','-ExecCmds="gt.Look.Weather Clear,t.MaxFPS 60"','-abslog="'+$projectRoot+'\Saved\Logs\BenmorePlay.log"')
# User-facing game launch is intentionally interactive.
Start-Process -FilePath $exe -ArgumentList $launchArgs

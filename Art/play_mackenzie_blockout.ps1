# Open the isolated playable blockout. No project defaults or saved progression are changed.
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$exe='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$launchArgs=@(('"'+$projectRoot+'\GrandTour.uproject"'),'/Game/GrandTour/Demo/MackenzieBlockout/L_Mackenzie_Blockout','-game','-windowed','-ResX=1600','-ResY=900','-GTNoLoad','-GTLook=0','-GTLookKuwahara=0','-ExecCmds="gt.Look.Weather Clear,t.MaxFPS 60"','-log=MackenziePlay.log')
# This is the interactive driving window, intentionally visible.
Start-Process -FilePath $exe -ArgumentList $launchArgs

$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$exe='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$argsList=@(('"'+$projectRoot+'\GrandTour.uproject"'),'/Game/GrandTour/Demo/BenmoreFullSite/L_Benmore_TerrainReview','-GTLook=0','-GTLookKuwahara=0','-GTNoLoad')
# User-facing editor launcher, intended for interactive terrain review.
Start-Process -FilePath $exe -ArgumentList $argsList

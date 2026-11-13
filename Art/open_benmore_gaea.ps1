# User-facing interactive launcher for the separate Gaea review map.
$ErrorActionPreference='Stop'
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is already running. Open L_Benmore_GaeaReview there, or close it before using this launcher.'}
if(Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object {$_.CommandLine -like '*Art/suite.sh*'}){throw 'The shared Unreal suite is still running. Wait for the suite to finish.'}
$projectRoot=Split-Path $PSScriptRoot
$editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview','-GTNoLoad','-GTLookKuwahara=0')
Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs

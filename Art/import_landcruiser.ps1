$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$busy=Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,FarCry6 -ErrorAction SilentlyContinue
if ($busy) { throw ('Close the running editor/game before importing: '+(($busy.ProcessName | Sort-Object -Unique)-join ', ')) }
& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/GrandTour.uproject" -run=pythonscript "-script=$projectRoot/Art/Unreal/import_landcruiser.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -FullStdOutLogOutput '-abslog=C:/GrandTour/Saved/Logs/import_landcruiser.log' *> "$projectRoot/Saved/Logs/import_landcruiser_console.log"
exit $LASTEXITCODE

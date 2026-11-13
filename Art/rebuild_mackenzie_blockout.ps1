$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$exe='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$content=Join-Path $projectRoot 'Content\GrandTour\Demo\MackenzieBlockout'
if(Test-Path -LiteralPath $content){
    $backup=Join-Path $projectRoot ('Saved\MackenzieBackups\'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Copy-Item -LiteralPath $content -Destination $backup -Recurse
}
$started=Get-Date
& $exe "$projectRoot\GrandTour.uproject" -run=pythonscript "-script=$projectRoot\Art\Unreal\setup_mackenzie_blockout.py" -NullRHI -unattended -nosplash -nosound "-abslog=$projectRoot\Saved\Logs\mackenzie_setup.log"
$file=Get-Item "$projectRoot\Art\Export\MackenzieBlockout\setup-report.json"
if($file.LastWriteTime -lt $started){throw 'No fresh setup report'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
$report | Select-Object ok,level,side_m,route_length_m,shortcut_length_m,max_sampled_grade_percent

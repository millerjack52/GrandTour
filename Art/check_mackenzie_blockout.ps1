$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$exe='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$argsList=@(('"'+$projectRoot+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLook=0','-GTLookKuwahara=0','-GTNoLoad','-ResX=1440','-ResY=900','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$projectRoot+'\Art\Unreal\check_mackenzie_blockout.py"'),('-abslog="'+$projectRoot+'\Saved\Logs\mackenzie_drive.log"'))
$started=Get-Date
$process=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
$process.WaitForExit()
$file=Get-Item "$projectRoot\Art\Export\MackenzieBlockout\drive-report.json"
if($file.LastWriteTime -lt $started){throw 'No fresh drive report'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
$report | Select-Object ok,pawn,collision,runs | ConvertTo-Json -Depth 6

$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\capture_gravel_road.py"'),('-abslog="'+$root+'\Saved\Logs\gravel_road_capture.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\GravelRoadUE\capture-report.json"
if($p.ExitCode -ne 0 -or $file.LastWriteTime -lt $started){throw 'Capture failed or report is stale'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'GRAVEL_ROAD_CAPTURE_OK'

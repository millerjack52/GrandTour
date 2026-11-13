param()
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied; no editor started'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal already running'}
 $started=Get-Date
 $qa=Join-Path $taskRoot 'Saved/LidarAuthoringQA/RS3'
 New-Item -ItemType Directory -Force -Path $qa | Out-Null
 $log=Join-Path $taskRoot 'Saved/Logs/LidarRiverPlantVariety-review.log'
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$log+'"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/check_lidar_river_plants.py"'))
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $processHandle=$p.Handle
 $p.WaitForExit();$code=$p.ExitCode
 $f=Get-Item "$taskRoot/Art/Export/LidarStudy/Place/rs3-river-view.json";$r=Get-Content -Raw -LiteralPath $f.FullName | ConvertFrom-Json
 @{exit_code=$code;started=$started.ToString('o');report_ok=$r.ok;report_written=$f.LastWriteTime.ToString('o');log=$log} | ConvertTo-Json | Set-Content "$qa/review-process.json"
 if($code -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw 'RS3 install failed; inspect report and process status'}
 if((Get-Content -Raw -LiteralPath $log) -match 'Failed to compile Material|LogShaderCompilers: Error'){throw 'RS3 material compilation failure'}
 $view=Get-Item "$taskRoot/Art/Export/LidarStudy/Place/rs3-river-view.json"
 $viewReport=Get-Content -LiteralPath $view.FullName -Raw | ConvertFrom-Json
 if(-not $viewReport.ok -or $view.LastWriteTime -lt $started){throw 'RS3 runtime capture failed'}
 Write-Output 'RS3 saved planting verified and runtime views captured'
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

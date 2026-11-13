param([ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='baseline',[ValidateSet('routes','slides','firm','access','steering','keyboard','water','performance','offroad','reversal')][string]$Mode='routes')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskLog="$taskRoot/Saved/Logs/DualDriving-$Label.log"
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskLog+'"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/check_lidar_dual_driving.py"'))
 if($Mode -in @('offroad','reversal')){
  $taskProfile=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
  $taskArgs+=('-ExecCmds="'+($taskProfile.commands -join ',')+'"')
 }
 $taskOld=$env:GT_DUAL_DRIVE_LABEL
 $taskOldMode=$env:GT_DUAL_DRIVE_MODE
 try {$env:GT_DUAL_DRIVE_LABEL=$Label;$env:GT_DUAL_DRIVE_MODE=$Mode;$taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru}finally{$env:GT_DUAL_DRIVE_LABEL=$taskOld;$env:GT_DUAL_DRIVE_MODE=$taskOldMode}
 $taskHandle=$taskProcess.Handle
 $taskProcess.WaitForExit()
 @{exit_code=$taskProcess.ExitCode;label=$Label;mode=$Mode;finished_utc=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/Saved/LidarAuthoringQA/Rally/$Label-process.json"
 $taskFile=Get-Item "$taskRoot/Saved/LidarAuthoringQA/Rally/$Label.json"
 if($taskFile.LastWriteTime -lt $taskStarted){throw 'No fresh report'}
 $taskResult=Get-Content $taskFile.FullName -Raw | ConvertFrom-Json
 $taskResult.runs | Select-Object car,road,low_range,distance_m,peak_kmh,max_off_m,max_gear,ok | Format-Table
 if($taskResult.comparisons){$taskResult.comparisons | Select-Object car,pattern,kmh,low,wheel_ratio,yaw_ratio,ok | Format-Table}
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode); inspect report and shutdown log separately"}
 if(-not $taskResult.ok){$taskFailures=(@($taskResult.runs | Where-Object {-not $_.ok} | ForEach-Object {"$($_.car) / $($_.road): $($_.aborted) distance=$($_.distance_m)"})+@($taskResult.comparisons | Where-Object {-not $_.ok} | ForEach-Object {"$($_.car) / $($_.pattern) at $($_.kmh): wheel ratio=$($_.wheel_ratio) yaw ratio=$($_.yaw_ratio)"})) -join '; ';throw "Driving check failed: $($taskResult.error) $taskFailures"}
} finally {if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

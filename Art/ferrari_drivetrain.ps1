param([ValidateSet('Baseline','Tune','Check','Consistency','Play')][string]$Mode='Play',
 [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='baseline')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskMap=if($Mode -eq 'Play'){'/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'}else{'/Engine/Maps/Entry'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),$taskMap,'-NoSplash','-NoSound','-nop4','-GTNoLoad','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/Ferrari-'+$Mode+'.log"'))
 $taskProfile=Get-Content -LiteralPath "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
 $taskArgs+=('-ExecCmds="'+($taskProfile.commands -join ',')+'"')
 if($Mode -eq 'Play') {$taskArgs+=@('-game','-windowed','-ResX=1600','-ResY=900','-GTFerrariTest')}
 else {
  $taskScript=if($Mode -eq 'Tune'){'tune_ferrari_driving.py'}elseif($Mode -eq 'Consistency'){'check_power_consistency.py'}else{'check_ferrari_drivetrain.py'}
  $taskArgs+=@('-Unattended','-RenderOffScreen',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'))
  if($Mode -eq 'Baseline'){$taskArgs+='-GTFerrariBaseline'}
 }
 $taskStyle=if($Mode -eq 'Play'){'Normal'}else{'Hidden'}
 $taskOldLabel=$env:GT_POWER_LABEL
 try {
  $env:GT_POWER_LABEL=$Label
  $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle $taskStyle -PassThru
 }finally{$env:GT_POWER_LABEL=$taskOldLabel}
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 if($Mode -ne 'Play'){
  $taskReportName=if($Mode -eq 'Consistency'){"consistency-$Label"}else{$Mode.ToLower()}
  $taskReport=Get-Item "$taskRoot/Saved/FerrariDrivingQA/$taskReportName.json"
  if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh Ferrari report'}
  if(-not (Get-Content $taskReport.FullName -Raw | ConvertFrom-Json).ok){throw 'Ferrari check failed; see Saved/FerrariDrivingQA'}
 }
 Write-Output "Ferrari $Mode completed"
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

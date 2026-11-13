param([ValidateSet('audit','install','check','coverage','foliage')][string]$Mode='audit')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskScript=if($Mode -eq 'audit'){'audit_lidar_polish.py'}elseif($Mode -eq 'coverage'){'lidar_water_coverage.py'}elseif($Mode -eq 'check'){'check_lidar_level_polish.py'}else{'lidar_level_polish.py'}
 $taskArguments=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/LidarPolish-'+$Mode+'.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'))
 $taskStarted=Get-Date
 $taskPreviousPhase=$env:GT_LP6_PHASE
 try {
  if($Mode -eq 'foliage'){$env:GT_LP6_PHASE='foliage'}else{$env:GT_LP6_PHASE=$null}
  $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
 }finally{$env:GT_LP6_PHASE=$taskPreviousPhase}
 $taskHandle=$taskProcess.Handle
 $taskProcess.WaitForExit()
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 $taskReport=Get-Item -LiteralPath "$taskRoot/Saved/LidarAuthoringQA/LP6/$Mode.json"
 if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh validation report'}
 $taskResult=Get-Content -LiteralPath $taskReport.FullName -Raw | ConvertFrom-Json
 if($Mode -ne 'audit' -and -not $taskResult.ok){throw "LP6 $Mode failed; inspect $($taskReport.FullName)"}
 if((Get-Content "$taskRoot/Saved/Logs/LidarPolish-$Mode.log" -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

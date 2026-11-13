param([ValidateSet('inspect','install','check','views')][string]$Mode='install')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskScript=if($Mode -in @('check','views')){'check_lidar_homestead.py'}else{'lidar_homestead.py'}
 $taskLog="$taskRoot/Saved/Logs/Homestead-$Mode.log"
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskLog+'"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'))
 $taskOld=$env:GT_HS1_MODE
 try {$env:GT_HS1_MODE=$Mode;$taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru}finally{$env:GT_HS1_MODE=$taskOld}
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 $taskFile=Get-Item "$taskRoot/Saved/LidarAuthoringQA/HS1/$Mode.json"
 if($taskFile.LastWriteTime -lt $taskStarted){throw 'No fresh report'}
 $taskResult=Get-Content $taskFile.FullName -Raw | ConvertFrom-Json
 if(-not $taskResult.ok){throw "HS1 $Mode failed: $($taskResult.error)"}
 Write-Output "HS1 $Mode passed"
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

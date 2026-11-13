param([switch]$Check)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskMode=if($Check){'check'}else{'install'}
 $taskLog="$taskRoot/Saved/Logs/LidarForest-FS1-$taskMode.log"
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskLog+'"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/lidar_forest_shapes.py"'))
 $taskOldCheck=$env:GT_FS1_CHECK
 try {
  $env:GT_FS1_CHECK=if($Check){'1'}else{'0'}
  $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 }finally{$env:GT_FS1_CHECK=$taskOldCheck}
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 $taskReport=Get-Item -LiteralPath "$taskRoot/Saved/LidarAuthoringQA/FS1/$taskMode.json"
 if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh FS1 report'}
 $taskResult=Get-Content -LiteralPath $taskReport.FullName -Raw | ConvertFrom-Json
 if(-not $taskResult.ok){throw "FS1 failed; inspect $($taskReport.FullName)"}
 if((Get-Content $taskLog -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
 Write-Output "FS1 $taskMode passed"
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

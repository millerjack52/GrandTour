param([switch]$Review)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskMode=if($Review){'review'}else{'install'}
 $taskLog="$taskRoot/Saved/Logs/LidarDust-GD1-$taskMode.log"
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskLog+'"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/lidar_gravel_dust.py"'))
 $taskOldCheck=$env:GT_GRAVEL_DUST_REVIEW
 try {
  $env:GT_GRAVEL_DUST_REVIEW=if($Review){'1'}else{'0'}
  $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 }finally{$env:GT_GRAVEL_DUST_REVIEW=$taskOldCheck}
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 $taskProcessReport=@{exit_code=$taskProcess.ExitCode;started=$taskStarted.ToString('o');finished=(Get-Date).ToString('o')}
 $taskProcessReport | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/Saved/LidarAuthoringQA/GD1/$taskMode-process.json"
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 $taskReport=Get-Item -LiteralPath "$taskRoot/Saved/LidarAuthoringQA/GD1/$taskMode.json"
 if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh GD1 report'}
 $taskResult=Get-Content -LiteralPath $taskReport.FullName -Raw | ConvertFrom-Json
 if(-not $taskResult.ok){throw "GD1 failed; inspect $($taskReport.FullName)"}
 if((Get-Content $taskLog -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
 Write-Output "GD1 $taskMode passed"
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

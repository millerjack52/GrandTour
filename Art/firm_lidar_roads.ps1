param([switch]$PresentationOnly)
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
 $taskLogName=$(if($PresentationOnly){'FirmRoads-Water'}else{'FirmRoads'})
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/'+$taskLogName+'.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/apply_lidar_firm_roads.py"'))
 $taskOldMode=$env:GT_FIRM_ROADS_PRESENTATION_ONLY
 try {$env:GT_FIRM_ROADS_PRESENTATION_ONLY=$(if($PresentationOnly){'1'}else{'0'});$taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru}finally{$env:GT_FIRM_ROADS_PRESENTATION_ONLY=$taskOldMode}
 $taskHandle=$taskProcess.Handle
 $taskProcess.WaitForExit()
 $taskReport=$(if($PresentationOnly){'water'}else{'apply'})
 $taskFile=Get-Item "$taskRoot/Saved/LidarAuthoringQA/FR1/$taskReport.json"
 if($taskFile.LastWriteTime -lt $taskStarted){throw 'No fresh report'}
 $taskResult=Get-Content $taskFile.FullName -Raw | ConvertFrom-Json
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode); inspect report and shutdown log separately"}
 if(-not $taskResult.ok){throw "Firm road rebuild failed: $($taskResult.error)"}
 Write-Output 'Firm gravel saved and reloaded. Owner drive pending.'
} finally {if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

param([switch]$Parallax)
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $started=Get-Date
 $qa=if($Parallax){'Saved/LidarAuthoringQA/RoadParallax/Review'}else{'Saved/LidarAuthoringQA/CohesiveRoads'}
 $launchArgs=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLookKuwahara=0','-GTLidarPerformance=0','-RenderOffScreen','-dx12','-abslog=C:/GrandTour/Saved/Logs/CohesiveRoads.log','-ExecutePythonScript=C:/GrandTour/Art/Unreal/check_cohesive_roads.py')
 $old=$env:GT_ROAD_PARALLAX_REVIEW;$env:GT_ROAD_PARALLAX_REVIEW=if($Parallax){'1'}else{'0'}
 try {$p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launchArgs -WindowStyle Hidden -PassThru} finally {$env:GT_ROAD_PARALLAX_REVIEW=$old}
 $null=$p.Handle;$p.WaitForExit()
 $f=Get-Item "$qa/check.json"
 $r=Get-Content $f.FullName -Raw | ConvertFrom-Json
 $log=Get-Content Saved/Logs/CohesiveRoads.log -Raw
 $shaderFailure=$log -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'
 @{exit_code=$p.ExitCode;started=$started.ToUniversalTime().ToString('o');report_ok=$r.ok;shader_validation_passed=(-not $shaderFailure);performance_verified=$false;gpu_timeout_warnings=([regex]::Matches($log,'GPU timeout:').Count)} | ConvertTo-Json | Set-Content "$qa/process.json"
 if($p.ExitCode -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started -or $shaderFailure){throw 'Road review failed; inspect check.json and log'}
 Write-Output 'Road review captures passed'
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

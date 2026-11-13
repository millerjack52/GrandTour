param([ValidateSet('audit','install','verify')][string]$Stage='audit')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $started=Get-Date;$old=$env:GT_ROAD_POM_STAGE;$env:GT_ROAD_POM_STAGE=$Stage
 try {
  $args2=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-NullRHI',"-abslog=C:/GrandTour/Saved/Logs/RoadParallax-$Stage.log",'-ExecutePythonScript=C:/GrandTour/Art/Unreal/road_parallax.py')
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args2 -WindowStyle Hidden -PassThru
 } finally {$env:GT_ROAD_POM_STAGE=$old}
 $null=$p.Handle;$p.WaitForExit();$f=Get-Item "Saved/LidarAuthoringQA/RoadParallax/$Stage.result.json";$r=Get-Content $f.FullName -Raw | ConvertFrom-Json
 @{exit_code=$p.ExitCode;started=$started.ToUniversalTime().ToString('o');result_ok=$r.ok} | ConvertTo-Json | Set-Content "Saved/LidarAuthoringQA/RoadParallax/$Stage-process.json"
 if(-not $r.ok -or $f.LastWriteTime -lt $started -or $p.ExitCode -ne 0){throw "Road parallax $Stage failed; inspect report"}
 Write-Output "Road parallax $Stage passed"
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

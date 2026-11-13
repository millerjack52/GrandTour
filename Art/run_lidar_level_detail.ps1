param([ValidateSet('prepare','install','verify')][string]$Stage='prepare')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $start=Get-Date;$old=$env:GT_DETAIL_STAGE;$env:GT_DETAIL_STAGE=$Stage
 try {
  $launchArgs=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-ExecCmds="t.MaxFPS 30"',"-abslog=C:/GrandTour/Saved/Logs/LevelDetail-$Stage.log",'-ExecutePythonScript=C:/GrandTour/Art/Unreal/lidar_level_detail.py')
  # Saved-data verification needs no renderer; actual rendered views are checked separately.
  if($Stage -eq 'verify'){$launchArgs=@($launchArgs | Where-Object {$_ -notin @('-dx12','-RenderOffScreen')});$launchArgs+='-NullRHI'}
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launchArgs -WindowStyle Hidden -PassThru
 } finally {$env:GT_DETAIL_STAGE=$old}
 $null=$p.Handle;$p.WaitForExit();$file=Get-Item "Saved/LidarAuthoringQA/LevelDetail/$Stage.json"
 if($file.LastWriteTime -lt $start){throw 'No current result'}
 $r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 @{stage=$Stage;exit_code=$p.ExitCode;result_ok=$r.ok;started=$start.ToUniversalTime().ToString('o');renderer=$(if($Stage -eq 'verify'){'NullRHI'}else{'DX12'})} | ConvertTo-Json | Set-Content "Saved/LidarAuthoringQA/LevelDetail/$Stage-process.json"
 if(-not $r.ok){throw $r.error};if($p.ExitCode -ne 0){throw "Editor exit $($p.ExitCode)"}
 Write-Output "LevelDetail $Stage passed"
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal already running'}
 $source=Join-Path $taskRoot 'Saved/LidarAuthoringBackups/RS6-1793920301782955600/L_LidarStudy.umap'
 $map=Join-Path $taskRoot 'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
 $expected=(Get-Content -Raw "$taskRoot/Saved/LidarAuthoringQA/RS5/install.json" | ConvertFrom-Json).map_sha256
 if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $expected){throw 'Backup does not match RS5'}
 $archive=Join-Path $taskRoot ('Saved/LidarAuthoringBackups/Rejected-RS6-'+(Get-Date -Format yyyyMMdd-HHmmss))
 New-Item -ItemType Directory -Path $archive | Out-Null
 Copy-Item -LiteralPath $map -Destination "$archive/L_LidarStudy.umap"
 Copy-Item -LiteralPath "$taskRoot/Art/Export/LidarStudy/Place/riverdetail.json" -Destination "$archive/riverdetail.json"
 Copy-Item -LiteralPath $source -Destination $map -Force
 if((Get-FileHash -LiteralPath $map -Algorithm SHA256).Hash -ne $expected){throw 'Restore hash mismatch'}
 Move-Item -LiteralPath "$taskRoot/Art/Export/LidarStudy/Place/rocky-bank.json" -Destination "$archive/rocky-bank.json"
 $launchArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/LidarRS6Rollback.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/check_lidar_rs6_rollback.py"'))
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launchArgs -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit()
 $r=Get-Content -Raw "$taskRoot/Saved/LidarAuthoringQA/RS6/rollback.json" | ConvertFrom-Json
 if($p.ExitCode -ne 0 -or -not $r.ok){throw 'Rollback verification failed'}
 if((Get-FileHash -LiteralPath $map -Algorithm SHA256).Hash -ne $expected){throw 'Restored map changed during readback'}
 Write-Output "Restored RS5; rejected RS6 archived at $archive"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

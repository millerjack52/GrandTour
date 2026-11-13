param([ValidateSet('Validate','Rebuild')][string]$Mode='Validate')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 $env:GT_RS7_MODE=$Mode;$started=Get-Date
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/rebuild_lidar_first_section.py"'),('-abslog="'+$taskRoot+'/Saved/Logs/LidarFirstSection-'+$Mode+'.log"'))
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit()
 $file=Get-Item "$taskRoot/Saved/LidarAuthoringQA/RS7/runner-$($Mode.ToLower()).json";$report=Get-Content $file.FullName -Raw | ConvertFrom-Json
 if($p.ExitCode -ne 0 -or -not $report.ok -or $file.LastWriteTime -lt $started){throw 'RS7 operation failed; inspect report'}
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

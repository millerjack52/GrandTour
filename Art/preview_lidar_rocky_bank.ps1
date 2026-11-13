param([switch]$Install)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal already running'}
 $script=if($Install){'install_lidar_rocky_bank.py'}else{'preview_lidar_rocky_bank.py'}
 $started=Get-Date
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/LidarRockyBank.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"'))
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw "Editor exit $($p.ExitCode)"}
 if($Install){
  $f=Get-Item "$taskRoot/Saved/LidarAuthoringQA/RS6/install.json";$r=Get-Content -Raw $f.FullName | ConvertFrom-Json
  if(-not $r.ok -or -not $r.reloaded -or $f.LastWriteTime -lt $started){throw 'RS6 install failed; inspect report'}
 }
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

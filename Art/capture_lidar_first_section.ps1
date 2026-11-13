param([string]$Label='baseline',[int]$FramesPerView=400,[string]$ViewsPath='',[string[]]$ExtraCommands=@(),[string[]]$StartupArguments=@(),[switch]$VisualOnly)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 $qa="$taskRoot/Saved/LidarAuthoringQA/RS7"
 if(-not $ViewsPath){$ViewsPath="$qa/cameras.json"}
 $views=Get-Content $ViewsPath -Raw | ConvertFrom-Json
 $preset=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
 # Visual reviews retain identical graphics and settle each view, but omit
 # benchmark sampling intervals when the GPU is shared with another app.
 $firstFrame=200;$shotOffset=280;$setupFrame=100;$extraFrame=110
 $schedule=@('50:EnableCheats','60:ShowHUD','60:DisableAllScreenMessages','150:ke GTCarPawn_0 SetActorHiddenInGame true')
 if($VisualOnly){$FramesPerView=96;$firstFrame=80;$shotOffset=48;$setupFrame=20;$extraFrame=30;$schedule=@('10:EnableCheats','15:ShowHUD','15:DisableAllScreenMessages','40:ke GTCarPawn_0 SetActorHiddenInGame true')}
 foreach($command in $preset.commands){$schedule+=($setupFrame.ToString()+':'+$command)}
 foreach($command in $ExtraCommands){$schedule+=($extraFrame.ToString()+':'+$command)}
 foreach($command in @('r.GPUCsvStatsEnabled 1','t.IdleWhenNotForeground 0','r.VSync 0')){$schedule+=($setupFrame.ToString()+':'+$command)}
 $index=0
 foreach($view in $views){
  $frame=$firstFrame+$index*$FramesPerView
  $schedule+=('{0}:BugItGo {1} {2} {3} 0 0 0' -f $frame,$view.position[0],$view.position[1],$view.position[2])
  $schedule+=('{0}:ViewActor {1}' -f ($frame+1),$view.actor)
  $schedule+=('{0}:HighResShot 1600x900 filename="{1}/{2}-{3}.png"' -f ($frame+$shotOffset),$qa,$Label,$view.view)
  $index++
 }
 $frames=$firstFrame+$views.Count*$FramesPerView
 $log="$taskRoot/Saved/Logs/LidarSection-$Label.log"
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="csv.UseLegacyFrameTime 0,CsvProfile FRAMES='+$frames+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($schedule -join ',')+'"'),('-abslog="'+$log+'"'))
 $launch+=@($StartupArguments)
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit()
 $logText=Get-Content $log -Raw
 $shaderFailures=@($logText -split "`n" | Where-Object {$_ -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'})
 $csvMatch=[regex]::Match($logText,'Writing CSV to file : ([^\r\n]+)')
 $csvPath=if($csvMatch.Success){[IO.Path]::GetFullPath((Join-Path 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64' $csvMatch.Groups[1].Value.Trim()))}else{''}
 $missingOrStale=@($views | Where-Object { $shot=Get-Item "$qa/$Label-$($_.view).png" -ErrorAction SilentlyContinue; -not $shot -or $shot.LastWriteTime -lt $started } | ForEach-Object {$_.view})
 @{label=$Label;exit_code=$p.ExitCode;started=$started.ToUniversalTime().ToString('o');csv=$csvPath;render_validation_passed=($shaderFailures.Count -eq 0 -and $missingOrStale.Count -eq 0);missing_or_stale_views=$missingOrStale;shader_failures=$shaderFailures;views=@($views | ForEach-Object {$_});commands=@($preset.commands);extra_commands=@($ExtraCommands);startup_arguments=@($StartupArguments);frames_per_view=$FramesPerView;visual_only=[bool]$VisualOnly;performance_verified=$false;gpu_timeout_warnings=([regex]::Matches($logText,'GPU timeout:').Count);capture='Standalone game, saved v6, 1600x900';log=$log} | ConvertTo-Json -Depth 8 | Set-Content "$qa/runtime-$Label.json"
 if($p.ExitCode -ne 0 -or -not $csvPath){throw 'Standalone capture failed'}
 if($shaderFailures.Count -gt 0){throw 'Shader fallback or compilation error invalidates this capture; see runtime report'}
 if($missingOrStale.Count -gt 0){throw 'Missing or stale screenshots invalidate this capture; see runtime report'}
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

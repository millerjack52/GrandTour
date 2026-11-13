param([ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='baseline',[string]$Commands='r.ScreenPercentage 100',[int]$FramesPerSite=1200,[switch]$Drive,[switch]$Probes,[switch]$UseSavedProfile,[switch]$Uncapped,[string]$PoseFile='',[string]$ExtraCommands='',[switch]$DistanceAB,[switch]$OnFoot,[switch]$Walk,[switch]$HighRange)
$ErrorActionPreference='Stop'
if($Walk){if($Drive -or $DistanceAB){throw 'Walk cannot combine with Drive or DistanceAB'};$OnFoot=$true}
if($DistanceAB -and ($Drive -or $FramesPerSite -lt 2200)){throw 'DistanceAB requires stationary views and at least 2200 frames per site'}
$taskRoot=Split-Path $PSScriptRoot
if($UseSavedProfile){
 $preset=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
 $profileCommands=@($preset.commands)
 if($Uncapped){$profileCommands=@($profileCommands | Where-Object {$_ -notmatch '^t.MaxFPS '})}
 $Commands=$profileCommands -join ','
}
if($ExtraCommands){$Commands+=','+$ExtraCommands}
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot reserved'}
 $out=Join-Path $taskRoot 'Art/Export/LidarStudy/Place'
 if(-not $PoseFile){$PoseFile="$out/pf60-poses.json"}
 $poses=Get-Content -LiteralPath $PoseFile -Raw | ConvertFrom-Json
 $schedule=@('50:EnableCheats')
 if($HighRange){$schedule+=@('150:Input.+action IA_LowRange 1','151:Input.-action IA_LowRange','152:Input.+action IA_DiffLock 1','153:Input.-action IA_DiffLock')}
 if($OnFoot){$schedule+=@('160:Input.+action IA_Exit 1','161:Input.-action IA_Exit')}
 foreach($cmd in ('t.MaxFPS 0,r.VSync 0,t.IdleWhenNotForeground 0,r.GPUCsvStatsEnabled 1,DisableAllScreenMessages,'+$Commands).Split(',')) {$schedule+=('100:'+$cmd)}
 $index=0
 foreach($pose in $poses) {
  $frame=200+$index*$FramesPerSite
  $schedule+=('{0}:BugItGo {1} {2} {3} 0 {4} 0' -f $frame,$pose.x,$pose.y,$pose.z,$pose.yaw)
  if($DistanceAB){$schedule+=('{0}:gt.Grass.Distance 1' -f $frame);$schedule+=('{0}:gt.Grass.Distance 0' -f ($frame+1700))}
  $schedule+=('{0}:HighResShot 1600x900 filename="{1}/PF60-{2}-{3}.png"' -f ($frame+250),($out.Replace('\','/')),$Label,$pose.name)
  if($Drive) {
   $schedule+=('{0}:LogLoc' -f ($frame+349))
   if($Probes){$schedule+=('{0}:gt.Perf.Reset' -f ($frame+349));$schedule+=('{0}:gt.Perf.LogSpikes 2' -f ($frame+349))}
   $schedule+=('{0}:Input.+key SpaceBar' -f ($frame+330))
   $schedule+=('{0}:Input.-key SpaceBar' -f ($frame+340))
   $schedule+=('{0}:Input.+action IA_Throttle 0.65' -f ($frame+350))
   $schedule+=('{0}:Input.-action IA_Throttle' -f ($frame+850))
   $schedule+=('{0}:LogLoc' -f ($frame+849))
   if($Probes){$schedule+=('{0}:gt.Perf.Dump PF60-{1}-{2}' -f ($frame+849),$Label,$pose.name);$schedule+=('{0}:gt.Perf.LogSpikes 0' -f ($frame+850))}
   $schedule+=('{0}:Input.+key SpaceBar' -f ($frame+851))
   $schedule+=('{0}:HighResShot 1600x900 filename="{1}/PF60-{2}-{3}-driven.png"' -f ($frame+950),($out.Replace('\','/')),$Label,$pose.name)
  }
  if($Walk) {
   $schedule+=('{0}:LogLoc' -f ($frame+349))
   if($Probes){$schedule+=('{0}:gt.Perf.Reset' -f ($frame+349));$schedule+=('{0}:gt.Perf.LogSpikes 2' -f ($frame+349))}
   $schedule+=('{0}:Input.+action IA_Move X=0 Y=1' -f ($frame+350))
   $schedule+=('{0}:Input.-action IA_Move' -f ($frame+850))
   $schedule+=('{0}:LogLoc' -f ($frame+849))
   if($Probes){$schedule+=('{0}:gt.Perf.Dump LP6-{1}-{2}' -f ($frame+849),$Label,$pose.name);$schedule+=('{0}:gt.Perf.LogSpikes 0' -f ($frame+850))}
   $schedule+=('{0}:HighResShot 1600x900 filename="{1}/PF60-{2}-{3}-walked.png"' -f ($frame+950),($out.Replace('\','/')),$Label,$pose.name)
  }
  $index++
 }
 $frames=200+$poses.Count*$FramesPerSite
 $log=Join-Path $taskRoot "Saved/Logs/LidarPlay-$Label.log"
 $before=@(Get-ChildItem "$taskRoot/Saved/Profiling/CSV" -Filter '*.csv' | ForEach-Object {$_.FullName})
 # A boot capture forces legacy FrameTime (work plus the next frame's variable wait).
 # Start through ExecCmds instead so UE measures logical frame boundaries after the cap wait.
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-GTLookKuwahara=0','-dx12',('-ExecCmds="csv.UseLegacyFrameTime 0,CsvProfile FRAMES='+$frames+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($schedule -join ',')+'"'),('-abslog="'+$log+'"'))
 $launch+='-GTLidarPerformance=0' # Explicit benchmark settings, never an implicit runtime preset.
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $handle=$p.Handle
 $p.WaitForExit()
 # Resolve the actual output path logged by UE (it can use the engine-user Saved folder).
 $csvMatch=[regex]::Match((Get-Content -LiteralPath $log -Raw),'Writing CSV to file : ([^\r\n]+)')
 $new=@()
 if($csvMatch.Success){$csvPath=[IO.Path]::GetFullPath((Join-Path 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64' $csvMatch.Groups[1].Value.Trim()));$new=@(Get-Item -LiteralPath $csvPath)}
 @{label=$Label;exit_code=$p.ExitCode;csv=@($new.FullName);poses=@($poses | ForEach-Object {$_});frames_per_site=$FramesPerSite;first_site_frame=200;commands=$Commands;log=$log;resolution=@(1600,900);drive=[bool]$Drive;walk=[bool]$Walk;on_foot=[bool]$OnFoot;high_range=[bool]$HighRange;distance_ab=[bool]$DistanceAB;frame_time_method='logical_after_tick_rate_wait';capture_mode='runtime'} | ConvertTo-Json -Depth 8 | Set-Content "$out/playperf-$Label.json"
 if($p.ExitCode -ne 0 -or $new.Count -ne 1){throw 'Standalone profile failed; inspect report'}
 Write-Output "Standalone $Label completed: $($new.FullName)"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

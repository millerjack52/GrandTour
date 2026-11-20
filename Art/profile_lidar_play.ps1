param([ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='baseline',[string]$Commands='r.ScreenPercentage 100',[int]$FramesPerSite=1200,[switch]$Drive,[switch]$Probes,[switch]$UseSavedProfile,[switch]$Uncapped,[string]$PoseFile='',[string]$ExtraCommands='',[switch]$DistanceAB,[switch]$OnFoot,[switch]$Walk,[switch]$HighRange,[switch]$DrivingBaseline,[ValidateSet('diagnose','cache','canopy','rebuild','drive','visual','routefilm','boundaryfilm','routehold','routetime','basepass','basemoving')][string]$ShadowStudy, [string]$ShadowCandidate='baseline',[ValidateSet('control','all_grass','near_grass','far_grass','trees','dressing','terrain','pickup','canopy_1','rain_capture','tree_wind')][string]$BaseFamily='control')
$ErrorActionPreference='Stop'
if($ShadowStudy){$DrivingBaseline=$true}
if($DrivingBaseline){
 $Drive=$true
 $Probes=$true
 $UseSavedProfile=$true
 $FramesPerSite=1350
 $PoseFile=Join-Path $PSScriptRoot 'lidar_driving_baseline_poses.json'
 if($DistanceAB -or $Walk -or $ExtraCommands -or $OnFoot -or $Uncapped -or $HighRange){throw 'Driving baseline uses the saved profile and fixed low-range drive inputs'}
}
if($Walk){if($Drive -or $DistanceAB){throw 'Walk cannot combine with Drive or DistanceAB'};$OnFoot=$true}
if($DistanceAB -and ($Drive -or $FramesPerSite -lt 2200)){throw 'DistanceAB requires stationary views and at least 2200 frames per site'}
$taskRoot=Split-Path $PSScriptRoot
if($UseSavedProfile){
 $preset=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
 $profileCommands=@($preset.commands)
 if($ShadowStudy -and $ShadowCandidate -ne 'saved'){
  # Historical experiments set their own shadow bias. Keep the v7 control reproducible.
  $profileCommands=@($profileCommands | Where-Object {$_ -notmatch '^r\.Shadow\.Virtual\.Clipmap\.WPODisableDistance\.LodBias '})
 }
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
 if($DrivingBaseline){
  $out=Join-Path $taskRoot "Saved/LidarDrivingBaseline/$Label"
  New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
  $os=Get-CimInstance Win32_OperatingSystem
  $minimumDisk = if($ShadowStudy -in @('basepass','basemoving')){3GB}else{4GB}
  if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB -or ([IO.DriveInfo]::new('C:\')).AvailableFreeSpace -lt $minimumDisk){throw 'Insufficient memory or disk for standalone drive'}
  if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender,'Wardogs*' -ErrorAction SilentlyContinue){throw 'Another renderer or Wardogs is active'}
  $conditions=@{
   map_sha256=(Get-FileHash -LiteralPath "$taskRoot/Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap").Hash
   preset_sha256=(Get-FileHash -LiteralPath "$PSScriptRoot/lidar_performance.json").Hash
   module_sha256=(Get-FileHash -LiteralPath "$taskRoot/Binaries/Win64/UnrealEditor-GrandTour.dll").Hash
   os_build=$os.BuildNumber
   cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)
   offscreen=$true
   audio_enabled=$true
  }
  $conditions | ConvertTo-Json | Set-Content "$out/conditions.json"
 }
 if(-not $PoseFile){$PoseFile="$out/pf60-poses.json"}
 $poses=Get-Content -LiteralPath $PoseFile -Raw | ConvertFrom-Json
 if($ShadowStudy){$poses=@($poses | Where-Object name -eq 'bog214')}
 $schedule=@('50:EnableCheats')
 if($DrivingBaseline){$schedule+='475:r.DumpRenderTargetPoolMemory'}
 if($HighRange){$schedule+=@('150:Input.+action IA_LowRange 1','151:Input.-action IA_LowRange','152:Input.+action IA_DiffLock 1','153:Input.-action IA_DiffLock')}
 if($OnFoot){$schedule+=@('160:Input.+action IA_Exit 1','161:Input.-action IA_Exit')}
 foreach($cmd in ('t.MaxFPS 0,r.VSync 0,t.IdleWhenNotForeground 0,r.GPUCsvStatsEnabled 1,DisableAllScreenMessages,'+$Commands).Split(',')) {$schedule+=('100:'+$cmd)}
 $index=0
 foreach($pose in $poses) {
  $frame=200+$index*$FramesPerSite
  $schedule+=('{0}:BugItGo {1} {2} {3} 0 {4} 0' -f $frame,$pose.x,$pose.y,$pose.z,$pose.yaw)
  if($ShadowStudy){
   & python "$PSScriptRoot/tools/lidar_shadow_study.py" schedule $ShadowStudy $ShadowCandidate $out $BaseFamily
   if($LASTEXITCODE -ne 0){throw 'Could not prepare shadow experiment'}
   $study=Get-Content -Raw -LiteralPath "$out/shadow-schedule.json" | ConvertFrom-Json
   $schedule+=@($study.commands)
   continue
  }
  if($DistanceAB){$schedule+=('{0}:gt.Grass.Distance 1' -f $frame);$schedule+=('{0}:gt.Grass.Distance 0' -f ($frame+1700))}
  if($DrivingBaseline){
   $schedule+=('{0}:Shot filename="{1}/{2}.png" -nosuffix' -f ($frame+280),$out.Replace('\','/'),$pose.name)
   $schedule+=('{0}:Input.-key SpaceBar' -f ($frame+450))
   $schedule+=('{0}:gt.Perf.Reset' -f ($frame+480))
   $schedule+=('{0}:gt.Perf.LogSpikes 2' -f ($frame+480))
   $schedule+=('{0}:Input.+action IA_Throttle 0.75' -f ($frame+500))
   foreach($offset in @(501,650,800,950,1100,1250)){ $schedule+=('{0}:LogLoc' -f ($frame+$offset)) }
   $schedule+=('{0}:Input.-action IA_Throttle' -f ($frame+1251))
   $schedule+=('{0}:gt.Perf.Dump {1}-{2}' -f ($frame+1252),$Label,$pose.name)
   $schedule+=('{0}:gt.Perf.LogSpikes 0' -f ($frame+1253))
   $schedule+=('{0}:Input.+key SpaceBar' -f ($frame+1254))
   if($pose.name -eq 'bog214'){
    # A post-window GPU event tree distinguishes which shadow rendering path is expensive.
    foreach($setting in @('r.ProfileGPU.ShowUI 0','r.ProfileGPU.UnicodeOutput 0','r.ProfileGPU.ThresholdPercent 0.5')){
     $schedule+=('{0}:{1}' -f ($frame+1260),$setting)
    }
    $schedule+=('{0}:ProfileGPU' -f ($frame+1261))
   }
   $index++
   continue
  }
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
 if($ShadowStudy){$frames=$study.frames}
 $log=Join-Path $taskRoot "Saved/Logs/LidarPlay-$Label.log"
 # CSV location is obtained from the runtime log.
 # A boot capture forces legacy FrameTime (work plus the next frame's variable wait).
 # Start through ExecCmds instead so UE measures logical frame boundaries after the cap wait.
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-GTLookKuwahara=0','-dx12',('-ExecCmds="csv.UseLegacyFrameTime 0,CsvProfile FRAMES='+$frames+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($schedule -join ',')+'"'),('-abslog="'+$log+'"'))
 $launch+='-GTLidarPerformance=0' # Explicit benchmark settings, never an implicit runtime preset.
 if($DrivingBaseline){
  $launch=@($launch | Where-Object {$_ -ne '-NoSound'})
  $launch+='-ForceRes'
  if($ShadowStudy){$launch+='-ForceEnablePython'}
  if($ShadowStudy -in @('visual','routefilm','boundaryfilm','routehold','basemoving')){$launch+=@('-UseFixedTimeStep','-FPS=24','-FixedSeed')}
  # The normal Saved/Profiling junction may point to a disconnected drive.
  $launch+='-saveddirsuffix=LidarDrive'
  $driveSaved=Join-Path $taskRoot 'Saved_LidarDrive'
  foreach($platform in @('WindowsEditor','Windows')){
   $gameSettings="Config/$platform/GameUserSettings.ini"
   if(Test-Path -LiteralPath "$taskRoot/Saved/$gameSettings"){
    New-Item -ItemType Directory -Force -Path "$driveSaved/Config/$platform" | Out-Null
    Copy-Item -LiteralPath "$taskRoot/Saved/$gameSettings" -Destination "$driveSaved/$gameSettings"
   }
  }
  $log=Join-Path $out 'drive.log'
  $launch=@($launch | Where-Object {$_ -notlike '-abslog=*'})
  $launch+=('-abslog="'+$log+'"')
 }
 if($ShadowStudy -and $ShadowCandidate -ne 'saved'){
  $trialPath=(Join-Path $PSScriptRoot 'Unreal/lidar_tree_shadow_trial.py').Replace('\','/')
  $startup=$null
  if($ShadowStudy -in @('drive','visual','routefilm','boundaryfilm','routehold','routetime','basepass') -and $ShadowCandidate -eq 'tree110'){
   $startup="py $trialPath"
  }elseif($preset.version -ge 8){
   $startup="py $trialPath stock"
  }
  if($startup){$launch=@($launch | ForEach-Object {if($_ -like '-ExecCmds=*'){ $_.TrimEnd('"')+','+$startup+'"' }else{$_}})}
 }
 if($ShadowStudy -and ($launch -join ' ').Length -ge 16200){throw 'Shadow study command line exceeds engine capacity'}
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $handle=$p.Handle
 if($DrivingBaseline){
  $gpuMonitor=$null
  $smi=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
  if($smi){
   $fields='timestamp,temperature.gpu,power.draw,utilization.gpu,clocks.sm,memory.used,clocks_event_reasons.sw_thermal_slowdown,clocks_event_reasons.sw_power_cap'
   $gpuMonitor=Start-Process $smi.Source -ArgumentList "--query-gpu=$fields",'--format=csv','--loop=10' -RedirectStandardOutput "$out/gpu-sample.csv" -WindowStyle Hidden -PassThru
  }
  $deadline=(Get-Date).AddMinutes(15)
  $waitingForCapture=$true
  try {
  while(-not $p.WaitForExit(2000)){
   if($waitingForCapture -and (Test-Path -LiteralPath $log)){
    if(Select-String -LiteralPath $log -SimpleMatch 'Capture will not start' -Quiet){
     Stop-Process -Id $p.Id -Force
     throw 'Unreal could not open the frame capture'
    }
    if(Select-String -LiteralPath $log -SimpleMatch 'CSVEvent "Cmd: EnableCheats"' -Quiet){$waitingForCapture=$false}
   }
   $other=Get-Process UnrealEditor,UnrealEditor-Cmd,blender,'Wardogs*' -ErrorAction SilentlyContinue | Where-Object Id -ne $p.Id
   if($other -or ([IO.DriveInfo]::new('C:\')).AvailableFreeSpace -lt 2GB -or (Get-Date) -gt $deadline){
    Stop-Process -Id $p.Id -Force
    throw 'Stopped this drive because another renderer started, storage ran low or the deadline expired'
   }
  }
  } finally {if($gpuMonitor -and -not $gpuMonitor.HasExited){$gpuMonitor.Kill()}}
 }else{$p.WaitForExit()}
 # Resolve the actual output path logged by UE (it can use the engine-user Saved folder).
 $csvMatch=[regex]::Match((Get-Content -LiteralPath $log -Raw),'Writing CSV to file : ([^\r\n]+)')
 $new=@()
 if($csvMatch.Success){
  $csvPath=$csvMatch.Groups[1].Value.Trim()
  if(-not [IO.Path]::IsPathRooted($csvPath)){$csvPath=Join-Path 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64' $csvPath}
  $new=@(Get-Item -LiteralPath ([IO.Path]::GetFullPath($csvPath)))
 }
 @{label=$Label;exit_code=$p.ExitCode;csv=@($new.FullName);poses=@($poses | ForEach-Object {$_});frames_per_site=$FramesPerSite;first_site_frame=200;commands=$Commands;log=$log;resolution=@(1600,900);drive=[bool]$Drive;walk=[bool]$Walk;on_foot=[bool]$OnFoot;high_range=[bool]$HighRange;distance_ab=[bool]$DistanceAB;frame_time_method='logical_after_tick_rate_wait';capture_mode='runtime'} | ConvertTo-Json -Depth 8 | Set-Content "$out/playperf-$Label.json"
 if($p.ExitCode -ne 0 -or $new.Count -ne 1){throw 'Standalone profile failed; inspect report'}
 Write-Output "Standalone $Label completed: $($new.FullName)"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

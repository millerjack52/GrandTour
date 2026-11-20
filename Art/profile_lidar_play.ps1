param([ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='baseline',[string]$Commands='r.ScreenPercentage 100',[int]$FramesPerSite=1200,[switch]$Drive,[switch]$Probes,[switch]$UseSavedProfile,[switch]$Uncapped,[string]$PoseFile='',[string]$ExtraCommands='',[switch]$DistanceAB,[switch]$OnFoot,[switch]$Walk,[switch]$HighRange,[switch]$DrivingBaseline,[ValidateSet('diagnose','cache','canopy','rebuild','drive','visual','routefilm','boundaryfilm','routehold','routetime','linkeddrive','basepass','basemoving','efficiency','weathercheck','visibilityhold','renderfamilies')][string]$ShadowStudy, [string]$ShadowCandidate='baseline',[ValidateSet('control','all_grass','near_grass','far_grass','trees','dressing','terrain','pickup','canopy_1','rain_capture','tree_wind','tree_visibility','tree_min2','tree_leaf_opaque','tree_nanite','mature_tree_nanite','mature_d003_nanite','mature_tree_paint','tree_paint','mature_d003_paint','tree_leaf_constant','dress_windlimit','tree_mask_threshold')][string]$BaseFamily='control',[string[]]$StudySettings=@(),[ValidateRange(0,1024)][int]$TreeCellMetres=0,[string]$EvidenceRoot='',[switch]$TreeMeshAudit,[switch]$TreeSections,[switch]$EarlyFamily,[ValidateSet('shadow','shadow_control')][string]$TreeShadowIndices,[switch]$ForegroundDrive,[switch]$TargetWindow,[ValidateSet('access','bog214','bog552')][string]$LinkedStart='access',[switch]$WarmTrees, [ValidateRange(0,150)][int]$NearTreeMetres=0, [switch]$NearTreeControl, [ValidateSet('depth','base')][string]$VelocityPassStudy, [switch]$StaticFarLeaves, [switch]$NativePlayer, [switch]$DisableEditorPython)
$ErrorActionPreference='Stop'
if($ShadowStudy){$DrivingBaseline=$true}
if($TargetWindow -and !$ForegroundDrive){throw 'The target window requires foreground timing'}
if($ShadowStudy -eq 'linkeddrive' -and !$ForegroundDrive){throw 'Continuous route timing requires the actual game window'}
if($ForegroundDrive -and ($ShadowStudy -notin @('routetime','linkeddrive') -or $ShadowCandidate -ne 'saved' -or $BaseFamily -ne 'control' -or $StudySettings -or $TreeCellMetres -or $TreeSections -or $TreeShadowIndices -or $Label.Length -gt 64)){throw 'Foreground timing uses the normal saved route and quality settings'}
if($DisableEditorPython -and !$NativePlayer){throw 'Disabling editor scripting requires the native route'}
if($NativePlayer -and (!$ForegroundDrive -or $ShadowStudy -ne 'routetime' -or $WarmTrees -or $VelocityPassStudy -or $StaticFarLeaves -or $NearTreeMetres -or $TreeMeshAudit)){throw 'The native launcher comparison requires an unmodified timed foreground drive'}
if($StaticFarLeaves){
 if(!$NearTreeMetres){$NearTreeMetres=110}
 if($NearTreeMetres -lt 110){throw 'Use at least the authored 110 m displacement cutoff for distant static leaves'}
 $NearTreeControl=$true
}
if($VelocityPassStudy -and (!$EvidenceRoot -or $ShadowCandidate -ne 'saved' -or $BaseFamily -ne 'control' -or $NearTreeMetres -or $StudySettings -or $TreeSections -or $TreeShadowIndices -or $TreeCellMetres -or $ShadowStudy -notin @('basemoving','routefilm','routetime'))){throw 'Motion-vector pass comparisons require the original trees and an external evidence folder'}
if($VelocityPassStudy){$WarmTrees=$true}
if($NearTreeControl -and !$NearTreeMetres){throw 'A near-tree control needs a distance'}
if($NearTreeMetres -and ($NearTreeMetres -lt 20 -or $ShadowCandidate -ne 'saved' -or $BaseFamily -ne 'control' -or $TreeCellMetres -or $TreeSections -or $TreeShadowIndices -or $StudySettings -or $ShadowStudy -notin @('routefilm','boundaryfilm','routetime','basemoving','linkeddrive'))){throw 'Near-tree comparisons require the saved route, original tree placement and a 20 to 150 metre distance'}
if($EarlyFamily -and $ShadowStudy -ne 'basemoving'){throw 'Early family installation requires a moving study'}
if($TreeShadowIndices){if($TreeSections){throw 'Choose a single canopy study'};$TreeSections=$true}
if($TreeSections -and ($TreeCellMetres -or $ShadowCandidate -ne 'saved' -or $ShadowStudy -notin @('basemoving','routefilm','routetime'))){throw 'Section study requires the saved trees and a driving comparison'}
if($TreeCellMetres -and ($ShadowStudy -ne 'basemoving' -or $TreeCellMetres -lt 32)){throw 'Tree cell trials require basemoving and at least 32 metres'}
if($StudySettings){
 if(-not $ShadowStudy){throw '-StudySettings requires a controlled study'}
 foreach($setting in $StudySettings){if($setting -notmatch '^(?:r|gt)\.[A-Za-z0-9_.]+ -?[0-9]+(?:\.[0-9]+)?$'){throw "Expected a numeric study setting: $setting"}}
}
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
  $profileCommands=@($profileCommands | Where-Object {$_ -notmatch '^(r\.Shadow\.Virtual\.Clipmap\.WPODisableDistance\.LodBias|gt\.Weather\.SkipDryOcclusion|r\.InstanceCulling\.OcclusionCull) '}) + @('gt.Weather.SkipDryOcclusion 0','r.InstanceCulling.OcclusionCull 0')
 }
 if($Uncapped){$profileCommands=@($profileCommands | Where-Object {$_ -notmatch '^t.MaxFPS '})}
 $Commands=$profileCommands -join ','
}
if($StudySettings){$Commands+=','+($StudySettings -join ',')}
if($ExtraCommands){$Commands+=','+$ExtraCommands}
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot reserved'}
 $out=Join-Path $taskRoot 'Art/Export/LidarStudy/Place'
 if($DrivingBaseline){
  $out=if($EvidenceRoot){Join-Path ([IO.Path]::GetFullPath($EvidenceRoot)) $Label}else{Join-Path $taskRoot "Saved/LidarDrivingBaseline/$Label"}
  New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
  $os=Get-CimInstance Win32_OperatingSystem
  $minimumDisk = if($ShadowStudy -in @('routetime','linkeddrive','basepass','basemoving','efficiency','weathercheck','visibilityhold','renderfamilies')){3GB}else{4GB}
  if($EvidenceRoot -and ([IO.DriveInfo]::new([IO.Path]::GetPathRoot($out))).AvailableFreeSpace -lt $minimumDisk){throw 'Insufficient storage for evidence'}
  $minSystemDisk=if($EvidenceRoot -and $ShadowStudy -in @('routefilm','boundaryfilm')){3584MB}else{$minimumDisk}
  if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB -or ([IO.DriveInfo]::new('C:\')).AvailableFreeSpace -lt $minSystemDisk){throw 'Insufficient memory or disk for standalone drive'}
  if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender,'Wardogs*' -ErrorAction SilentlyContinue){throw 'Another renderer or Wardogs is active'}
  $conditions=@{
   map_sha256=(Get-FileHash -LiteralPath "$taskRoot/Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap").Hash
   preset_sha256=(Get-FileHash -LiteralPath "$PSScriptRoot/lidar_performance.json").Hash
   module_sha256=(Get-FileHash -LiteralPath "$taskRoot/Binaries/Win64/UnrealEditor-GrandTour.dll").Hash
   os_build=$os.BuildNumber
   cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)
   offscreen=(!$ForegroundDrive)
   audio_enabled=$true
  }
  $workshopSave=Join-Path $taskRoot 'Saved_LidarDrive/SaveGames/GT_Workshop_RangeRover.sav'
  $conditions.workshop_save_sha256=if(Test-Path -LiteralPath $workshopSave){(Get-FileHash -LiteralPath $workshopSave).Hash}else{$null}
  $conditions.near_tree_metres=$NearTreeMetres
  $conditions.near_tree_control=[bool]$NearTreeControl
  $conditions.velocity_pass_trial=$VelocityPassStudy
  $conditions.static_far_leaves=[bool]$StaticFarLeaves
  $conditions.native_player=[bool]$NativePlayer
  $conditions.disable_editor_python=[bool]$DisableEditorPython
  $conditions | ConvertTo-Json | Set-Content "$out/conditions.json"
 }
 if(-not $PoseFile){$PoseFile="$out/pf60-poses.json"}
 $poses=Get-Content -LiteralPath $PoseFile -Raw | ConvertFrom-Json
 if($ShadowStudy){$poses=@($poses | Where-Object name -eq 'bog214')}
 $schedule=@('50:EnableCheats')
 if($DrivingBaseline){$schedule+='475:r.DumpRenderTargetPoolMemory'}
 if($HighRange){$schedule+=@('150:Input.+action IA_LowRange 1','151:Input.-action IA_LowRange','152:Input.+action IA_DiffLock 1','153:Input.-action IA_DiffLock')}
 if($OnFoot){$schedule+=@('160:Input.+action IA_Exit 1','161:Input.-action IA_Exit')}
 if($ForegroundDrive){
  $schedule+='100:r.GPUCsvStatsEnabled 1'
 }else{
  foreach($cmd in ('t.MaxFPS 0,r.VSync 0,t.IdleWhenNotForeground 0,r.GPUCsvStatsEnabled 1,DisableAllScreenMessages,'+$Commands).Split(',')){$schedule+=('100:'+$cmd)}
 }
 $index=0
 foreach($pose in $poses) {
  $frame=200+$index*$FramesPerSite
  $schedule+=('{0}:BugItGo {1} {2} {3} 0 {4} 0' -f $frame,$pose.x,$pose.y,$pose.z,$pose.yaw)
  if($ShadowStudy){
   & python "$PSScriptRoot/tools/lidar_shadow_study.py" schedule $ShadowStudy $ShadowCandidate $out $BaseFamily ([int]$EarlyFamily.IsPresent) $LinkedStart ([int]$NativePlayer.IsPresent) ([int]($WarmTrees -or $NearTreeMetres -or $BaseFamily.EndsWith('_paint')))
   if($LASTEXITCODE -ne 0){throw 'Could not prepare shadow experiment'}
   $study=Get-Content -Raw -LiteralPath "$out/shadow-schedule.json" | ConvertFrom-Json
   $schedule+=@($study.commands)
   if($ForegroundDrive -and $ShadowStudy -ne 'linkeddrive'){
    $schedule+="415:gt.Lidar.Present start $Label"
    foreach($window in $study.windows){
     $schedule+=('{0}:gt.Lidar.Present mark {1}' -f $window.start,$window.name)
     $schedule+=('{0}:gt.Lidar.Present mark None' -f $window.end)
    }
    $schedule+=('{0}:gt.Lidar.Present stop' -f ($study.frames-8))
   }
   if($ShadowStudy -eq 'basemoving'){$schedule+='592:gt.Lidar.AuditTreeRendering'}
   if($NearTreeMetres){
    $mode=if($NearTreeControl){'control'}else{'paint'}
    $schedule+=("342:gt.Lidar.NearTreeStudy $NearTreeMetres $mode")
    if($StaticFarLeaves){
     $farScript=(Join-Path $PSScriptRoot 'Unreal/lidar_distant_leaf_trial.py').Replace('\','/')
     $schedule+=("345:py $farScript")
    }
   }
   if($WarmTrees -or $NearTreeMetres -or $BaseFamily.EndsWith('_paint')){
    if($ShadowStudy -eq 'basemoving'){$schedule+='468:gt.Lidar.AuditTreeRendering warm'}
    if($ShadowStudy -in @('routefilm','boundaryfilm','routetime','linkeddrive')){$schedule+=@('425:gt.Lidar.AuditTreeRendering warm','455:gt.Lidar.AuditTreeRendering')}
   }
   if($VelocityPassStudy){
    if($ShadowStudy -eq 'basemoving'){$schedule+=@('448:gt.Lidar.AuditRenderPass warm','611:gt.Lidar.AuditRenderPass','821:gt.Lidar.AuditRenderPass')}
    else{$schedule+=@('416:gt.Lidar.AuditRenderPass warm','485:gt.Lidar.AuditRenderPass')}
   }
   if($TreeMeshAudit){$audit=(Join-Path $PSScriptRoot 'Unreal/lidar_tree_mesh_audit.py').Replace('\','/');$schedule+=(('{0}:py {1} {2}' -f ($study.frames-5),$audit,$out.Replace('\','/')))}
   if($TreeSections){$schedule+=('342:gt.Lidar.TrialTreeSections '+$TreeShadowIndices).TrimEnd()}
   if($TreeCellMetres){$schedule+=('404:gt.Lidar.TrialTreeCells '+$TreeCellMetres)}
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
  if($ShadowStudy -and !$NativePlayer){$launch+='-ForceEnablePython'}
  if($ShadowStudy -in @('visual','routefilm','boundaryfilm','routehold','basemoving','efficiency','weathercheck','visibilityhold','renderfamilies')){$launch+=@('-UseFixedTimeStep','-FPS=24','-FixedSeed')}
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
  if($ShadowStudy -in @('drive','visual','routefilm','boundaryfilm','routehold','routetime','linkeddrive','basepass') -and $ShadowCandidate -eq 'tree110'){
   $startup="py $trialPath"
  }elseif($preset.version -ge 8){
   $startup="py $trialPath stock"
  }
  if($startup){$launch=@($launch | ForEach-Object {if($_ -like '-ExecCmds=*'){ $_.TrimEnd('"')+','+$startup+'"' }else{$_}})}
 }

 $windowStyle='Hidden'
 if($ForegroundDrive){
  $launch=@($launch | Where-Object {$_ -notin @('-Unattended','-RenderOffScreen','-ForceRes','-GTLidarPerformance=0')} | ForEach-Object {
   if($_ -like '-ExecCmds=*'){$_.Replace('-ExecCmds="','-ExecCmds="'+($preset.commands -join ',')+',')}else{$_}
  })
  if($TargetWindow){$launch+=@('-ForceRes','-ini:Engine:[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True')}
  $windowStyle='Normal'
 }
 if($DisableEditorPython){$launch+='-DisablePython'}
 if($NativePlayer -and (($launch -join ' ') -match 'ForceEnablePython|:py ')){throw 'Unexpected scripting in the native drive'}
 if($ShadowStudy -and ($launch -join ' ').Length -ge 16200){throw 'Shadow study command line exceeds engine capacity'}
 if($VelocityPassStudy){
  $scratch=Join-Path ([IO.Path]::GetFullPath($EvidenceRoot)) 'VelocityShaders'
  if(([IO.Path]::GetPathRoot($scratch) -eq [IO.Path]::GetPathRoot($env:SystemRoot)) -or ([IO.DriveInfo]::new([IO.Path]::GetPathRoot($scratch))).AvailableFreeSpace -lt 20GB){throw 'The shader comparison needs 20 GB on the evidence drive'}
  $shaderCache=Join-Path $scratch 'Cache'
  $shaderTemp=Join-Path $scratch 'Temp'
  New-Item -ItemType Directory -Force -Path $shaderCache,$shaderTemp | Out-Null
  $passValue=[int]($VelocityPassStudy -eq 'base')
  $launch+=@("-ini:Engine:[/Script/Engine.RendererSettings]:r.VelocityOutputPass=$passValue",
   '-DDC=(EnginePak=InstalledEnginePak,ZenLocal(ReadOnly=true),Prior=InstalledLocal(ReadOnly=true),Scratch=Shared)',
   ('-SharedDataCachePath="'+$shaderCache+'"'))
 }
 $savedTemp=$env:TEMP
 $savedTmp=$env:TMP
 try{
  if($VelocityPassStudy){$env:TEMP=$shaderTemp;$env:TMP=$shaderTemp}
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle $windowStyle -PassThru
 }finally{$env:TEMP=$savedTemp;$env:TMP=$savedTmp}
 $handle=$p.Handle
 if($DrivingBaseline){
  $gpuMonitor=$null
  $smi=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
  if($smi){
   $fields='timestamp,temperature.gpu,power.draw,utilization.gpu,clocks.sm,memory.used,clocks_event_reasons.sw_thermal_slowdown,clocks_event_reasons.sw_power_cap'
   $gpuMonitor=Start-Process $smi.Source -ArgumentList "--query-gpu=$fields",'--format=csv','--loop=1' -RedirectStandardOutput "$out/gpu-sample.csv" -WindowStyle Hidden -PassThru
  }
  $allowedMinutes=if($VelocityPassStudy){45}else{15}
  $deadline=(Get-Date).AddMinutes($allowedMinutes)
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
 if($DrivingBaseline){
  $conditions.final_workshop_save_sha256=if(Test-Path -LiteralPath $workshopSave){(Get-FileHash -LiteralPath $workshopSave).Hash}else{$null}
  $conditions | ConvertTo-Json | Set-Content "$out/conditions.json"
 }
 if($ForegroundDrive){
  $presentationPath=Join-Path $driveSaved "LidarPresentation/$Label.csv"
  if(!(Test-Path -LiteralPath $presentationPath) -or !(Select-String -LiteralPath $log -SimpleMatch 'GT_LIDAR_PRESENT saved=1' -Quiet)){throw 'No window presentation capture'}
  Copy-Item -LiteralPath $presentationPath -Destination (Join-Path $out 'presentation.csv')
  $actualSizes=@(Import-Csv -LiteralPath $presentationPath | ForEach-Object {"$($_.width)x$($_.height)"} | Sort-Object -Unique)
  $conditions.presentation_viewports=$actualSizes
  $conditions.target_window=[bool]$TargetWindow
  $conditions | ConvertTo-Json | Set-Content "$out/conditions.json"
  if($TargetWindow -and ($actualSizes.Count -ne 1 -or $actualSizes[0] -ne '1600x900')){throw 'Game window did not reach the target resolution'}
 }
 if($StaticFarLeaves){
  if(!(Select-String -LiteralPath $log -SimpleMatch 'GT_STATIC_LEAF_RANGE groups=3' -Quiet)){throw 'The distant-tree wind boundary did not verify'}
  foreach($species in 0..2){
   $near="GT_TREE_DRAW_RANGE mesh=SM_Canopy_$species min_cm=0 max_cm=$($NearTreeMetres*100) wpo_slots=1"
   $far="GT_TREE_DRAW_RANGE mesh=SM_Canopy_$species min_cm=$($NearTreeMetres*100) max_cm=2147483648 wpo_slots=0"
   if(!(Select-String -LiteralPath $log -SimpleMatch $near -Quiet) -or !(Select-String -LiteralPath $log -SimpleMatch $far -Quiet)){throw "Compiled leaf wind did not match the near and far ranges for species $species"}
  }
 }
 if($VelocityPassStudy){
  $lastPass=Select-String -LiteralPath $log -SimpleMatch 'GT_LIDAR_PASS velocity=' | Select-Object -Last 1
  if(!$lastPass -or !$lastPass.Line.Contains("GT_LIDAR_PASS velocity=$passValue pending_assets=0")){throw 'Motion-vector setting or compilation did not verify'}
  if(Select-String -LiteralPath $log -Pattern 'Failed to compile (global shader|Material)|Default Material will be used in game' -Quiet){throw 'A material failed to compile in the motion-vector comparison'}
  $cacheLine=Select-String -LiteralPath $log -Pattern 'Scratch: Using.*Writable' | Select-Object -First 1
  if(!$cacheLine -or !$cacheLine.Line.Replace('\','/').Contains($shaderCache.Replace('\','/'))){throw 'Could not verify the isolated shader cache'}
 }
 if($NearTreeMetres -or $BaseFamily.EndsWith('_paint') -or $WarmTrees){
  $groups=6
  $expectedProxies=0
  if($NearTreeMetres){
   $groups=9
   $paint=[int](!$NearTreeControl)
   $expectedProxies=3*$paint
   if(!(Select-String -LiteralPath $log -SimpleMatch "GT_TREE_RANGE groups=3 instances=146197 radius_cm=$($NearTreeMetres*100) painted=$paint" -Quiet)){throw 'Near-tree distances were not installed on all three mature species'}
   foreach($species in 0..2){
    $nearMesh=if($NearTreeControl){"SM_Canopy_$species"}else{"SM_NanitePainted_$species"}
    foreach($range in @("mesh=$nearMesh min_cm=0 max_cm=$($NearTreeMetres*100)","mesh=SM_Canopy_$species min_cm=$($NearTreeMetres*100) max_cm=2147483648")){
     if(!(Select-String -LiteralPath $log -SimpleMatch "GT_TREE_DRAW_RANGE $range" -Quiet)){throw "Missing renderer distance check: $range"}
    }
   }
  }elseif($BaseFamily.EndsWith('_paint')){
   $expectedProxies=@{tree_paint=6;mature_tree_paint=3;mature_d003_paint=1}[$BaseFamily]
  }
  $lastAudit=Select-String -LiteralPath $log -SimpleMatch 'GT_TREE_RENDER_SUMMARY groups=' | Select-Object -Last 1
  if(!$lastAudit -or !$lastAudit.Line.Contains("GT_TREE_RENDER_SUMMARY groups=$groups proxies=$groups nanite=$expectedProxies material_fallbacks=0")){throw 'Tree renderer or materials not verified'}
 }
 if($ShadowStudy -eq 'linkeddrive'){
  $routeReport=Get-Content -LiteralPath (Join-Path $out 'continuous-drive.json') -Raw | ConvertFrom-Json
  if(!$routeReport.samples.Count -or $routeReport.reason -eq 'probe_error'){throw 'Physical route telemetry did not produce a driving sample'}
  if($routeReport.reason -ne 'end_of_route'){Write-Warning "Partial physical drive ended with $($routeReport.reason)"}
 }
 $expectedParts=if($TreeShadowIndices){6}else{12}
 if($TreeSections -and !(Select-String -LiteralPath $log -SimpleMatch "GT_TREE_SECTIONS_READY groups=6 trees=159227 parts=$expectedParts" -Quiet)){throw 'The canopy section study did not activate'}
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

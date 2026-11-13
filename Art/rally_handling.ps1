param([ValidateSet('Install','Polish','Recess','Surface','Feedback','Corners','Tests','Review','Play','Editor')][string]$Mode='Play',
 [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='baseline',
 [ValidateSet(0,1)][int]$CountersteerResponse=1,[switch]$Fleet,[switch]$RangeRoverAudio,[switch]$Ferrari,[switch]$RecoveryDriver)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskLog="$taskRoot/Saved/Logs/RallyHandling-$Mode-$Label.log"
 $taskMap='/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'
 $taskOpenMap=if($Mode -in @('Install','Polish','Recess','Surface','Feedback','Corners','Tests','Review')){'/Engine/Maps/Entry'}else{$taskMap}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),$taskOpenMap,'-NoSplash','-NoSound','-nop4','-GTNoLoad','-dx12',('-abslog="'+$taskLog+'"'))
 if($RangeRoverAudio){
  if($Mode -notin @('Play','Editor')){throw 'RangeRoverAudio is a driving/editor audition option'}
  $taskArgs=@($taskArgs | Where-Object {$_ -ne '-NoSound'})
  $taskArgs+='-GTRangeRoverAudioTest'
 }
 if($Mode -in @('Feedback','Corners','Review','Play')){
  $taskProfile=Get-Content -LiteralPath "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
  $taskCommands=(@($taskProfile.commands)+"gt.Vehicle.CountersteerResponse $CountersteerResponse") -join ','
  $taskArgs+=('-ExecCmds="'+$taskCommands+'"')
 }
 if($Mode -eq 'Tests'){
  $taskArgs+=@('-NullRHI','-Unattended','-ExecCmds="Automation RunTests GrandTour.Spray.Art+GrandTour.DustLab+GrandTour.Vehicle.ResponsiveSteering+GrandTour.Vehicle.CountersteerResponse+GrandTour.Vehicle.SlideRecovery+GrandTour.LandscapeMud.DirectionalSoilFlow+GrandTour.LandscapeMud.RutWallWork+GrandTour.MudRunner.LivePush+GrandTour.MudRunner.SubstanceOracle+GrandTour.Water.MovingDomain+GrandTour.Water.RiverReference+GrandTour.Water.ShoreEnvelope"','-TestExit="Automation Test Queue Empty"',('-ReportExportPath="'+$taskRoot+'/Saved/Automation/RallyHandling-'+$Label+'"'))
 } elseif($Mode -in @('Install','Polish','Recess','Surface','Feedback','Corners','Review')) {
  if($Mode -in @('Install','Polish')){
   & "$taskRoot/Saved/Tools/TerrainPython/Scripts/python.exe" "$taskRoot/Art/tools/prepare_rally_handling.py"
   if($LASTEXITCODE -ne 0){throw 'Course preparation failed'}
  }
  $taskScript=if($Mode -eq 'Corners'){'check_rally_corners.py'}elseif($Mode -eq 'Feedback'){'check_rally_feedback.py'}else{'setup_rally_handling.py'}
  $taskArgs+=@('-Unattended','-RenderOffScreen',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'))
 } else {
  if($Mode -eq 'Play'){
   $taskArgs+=@('-game','-windowed','-ResX=1600','-ResY=900')
  }
 }
 $taskOldMode=$env:GT_RALLY_HANDLING_MODE
 $taskOldLabel=$env:GT_RALLY_HANDLING_LABEL
 $taskOldCountersteer=$env:GT_RALLY_COUNTERSTEER
 $taskOldFleet=$env:GT_RALLY_FLEET
 $taskOldFerrari=$env:GT_RALLY_FERRARI
 $taskOldDriver=$env:GT_RALLY_DRIVER
 try {
  $env:GT_RALLY_HANDLING_MODE=$Mode
  $env:GT_RALLY_HANDLING_LABEL=$Label
  $env:GT_RALLY_COUNTERSTEER=[string]$CountersteerResponse
  $env:GT_RALLY_FLEET=if($Fleet){'1'}else{'0'}
  $env:GT_RALLY_FERRARI=if($Ferrari){'1'}else{'0'}
  $env:GT_RALLY_DRIVER=if($RecoveryDriver){'3'}else{'2'}
  $taskWindowStyle=if($Mode -in @('Install','Polish','Recess','Surface','Feedback','Corners','Tests','Review')){'Hidden'}else{'Normal'}
  $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle $taskWindowStyle -PassThru
 }finally{$env:GT_RALLY_HANDLING_MODE=$taskOldMode;$env:GT_RALLY_HANDLING_LABEL=$taskOldLabel;$env:GT_RALLY_COUNTERSTEER=$taskOldCountersteer;$env:GT_RALLY_FLEET=$taskOldFleet;$env:GT_RALLY_FERRARI=$taskOldFerrari;$env:GT_RALLY_DRIVER=$taskOldDriver}
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 if($Mode -eq 'Tests'){
  if($taskProcess.ExitCode -ne 0){throw "Automation process failed: $($taskProcess.ExitCode)"}
  $taskTestReport=Get-Item "$taskRoot/Saved/Automation/RallyHandling-$Label/index.json"
  if($taskTestReport.LastWriteTime -lt $taskStarted){throw 'No fresh automation report'}
  $taskTests=Get-Content $taskTestReport.FullName -Raw | ConvertFrom-Json
  if($taskTests.failed -ne 0 -or ($taskTests.succeeded+$taskTests.succeededWithWarnings) -lt 13){throw 'Selected regression tests did not all pass'}
  Write-Output "Rally regression tests passed"
 }
 if($Mode -in @('Install','Polish','Recess','Surface','Feedback','Corners','Review')){
  $taskReportName=if($Mode -in @('Corners','Feedback')){$Mode.ToLower()+'-'+$Label}else{$Mode.ToLower()}
  $taskProcessReport=@{exit_code=$taskProcess.ExitCode;started=$taskStarted.ToString('o');finished=(Get-Date).ToString('o')}
  $taskProcessReport | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/Saved/RallyHandlingQA/$taskReportName-process.json"
  if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
  $taskReport=Get-Item -LiteralPath "$taskRoot/Saved/RallyHandlingQA/$taskReportName.json"
  if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh rally report'}
  $taskResult=Get-Content -LiteralPath $taskReport.FullName -Raw | ConvertFrom-Json
  if(-not $taskResult.ok){throw "Rally $Mode failed; inspect $($taskReport.FullName)"}
  if((Get-Content $taskLog -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
  Write-Output "Rally $Mode passed"
 }
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

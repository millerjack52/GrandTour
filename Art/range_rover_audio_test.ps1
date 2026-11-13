param([ValidateSet('Tests','Drive')][string]$Mode='Tests',[switch]$CpuOnly)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
if($Mode -eq 'Tests'){
 & "$taskRoot/Saved/Tools/TerrainPython/Scripts/python.exe" "$taskRoot/Art/tools/check_range_rover_h2_runtime.py"
 if($LASTEXITCODE -ne 0){throw 'Independent H2 reference preparation failed'}
}
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskLog="$taskRoot/Saved/Logs/RangeRoverH2-$Mode.log"
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-NoSplash','-Unattended','-nop4','-GTNoLoad',('-abslog="'+$taskLog+'"'))
 if($Mode -eq 'Tests'){
  $taskArgs+=@('-NullRHI','-NoSound','-ExecCmds="Automation RunTests GrandTour.Vehicle.RangeRoverHybridH2+GrandTour.Vehicle.GroundAudio"','-TestExit="Automation Test Queue Empty"',('-ReportExportPath="'+$taskRoot+'/Saved/Automation/RangeRoverH2"'))
 }else{
  $taskProfile=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
  $taskArgs+=@('-RenderOffScreen','-dx12','-GTRangeRoverAudioTest',('-ExecCmds="'+($taskProfile.commands -join ',')+'"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/check_range_rover_audio.py"'))
  if($CpuOnly){$taskArgs=@($taskArgs | Where-Object {$_ -notin @('-RenderOffScreen','-dx12')});$taskArgs+='-NullRHI'}
 }
 $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 if($Mode -eq 'Tests'){
  $taskReport=Get-Item "$taskRoot/Saved/Automation/RangeRoverH2/index.json"
  if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh test report'}
  $taskResult=Get-Content $taskReport.FullName -Raw | ConvertFrom-Json
  if($taskResult.failed -ne 0 -or $taskResult.succeeded -ne 2){throw 'Engine/ground renderer tests failed'}
 }else{
  $taskReport=Get-Item "$taskRoot/Saved/AudioH2QA/drive.json"
  if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh drive report'}
  $taskResult=Get-Content $taskReport.FullName -Raw | ConvertFrom-Json
  if(-not $taskResult.ok){throw 'H2 driving smoke test failed'}
  $taskText=Get-Content $taskLog -Raw
  if($taskText -notmatch 'RangeRover H2: rpm=\d+ throttle=[\d.]+ audible=1 playing=1 rendered_frames=[1-9]\d*'){throw 'No confirmed audio render callbacks'}
 }
 Write-Output "RangeRover H2 $Mode passed"
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

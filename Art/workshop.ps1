param([ValidateSet('Setup','WheelSetup','EquipmentSetup','Check','DrivetrainCheck','LayoutCheck','BiasCheck','Play')][string]$Mode='Play')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable'}
$taskMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$taskHeld=$false
try {
 try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if(-not $taskHeld){throw 'Unreal slot reserved'}
 $taskStarted=Get-Date
 $taskMap=if($Mode -eq 'Play'){'/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'}else{'/Engine/Maps/Entry'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),$taskMap,'-NoSplash','-nop4','-GTNoLoad','-dx12','-GTRangeRoverAudioTest',('-abslog="'+$taskRoot+'/Saved/Logs/Workshop-'+$Mode+'.log"'))
 $taskProfile=Get-Content -LiteralPath "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
 $taskArgs+=('-ExecCmds="'+($taskProfile.commands -join ',')+'"')
 if($Mode -eq 'Play') {$taskArgs+=@('-game','-windowed','-ResX=1600','-ResY=900')}
 else {
  $taskScript=if($Mode -eq 'Setup'){'setup_workshop.py'}elseif($Mode -eq 'WheelSetup'){'setup_workshop_wheels.py'}elseif($Mode -eq 'EquipmentSetup'){'setup_workshop_equipment.py'}elseif($Mode -eq 'DrivetrainCheck'){'check_rr_drivetrain.py'}elseif($Mode -eq 'LayoutCheck'){'check_drive_layout.py'}elseif($Mode -eq 'BiasCheck'){'check_awd_bias.py'}else{'check_workshop.py'}
  $taskArgs+=@('-Unattended','-RenderOffScreen',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'))
  if($Mode -in @('Check','DrivetrainCheck','LayoutCheck','BiasCheck')){$taskArgs+='-GTWorkshopQA'}
 }
 $taskStyle=if($Mode -eq 'Play'){'Normal'}else{'Hidden'}
 $taskProcess=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle $taskStyle -PassThru
 $taskHandle=$taskProcess.Handle;$taskProcess.WaitForExit()
 if($taskProcess.ExitCode -ne 0){throw "Unreal exit $($taskProcess.ExitCode)"}
 if($Mode -ne 'Play'){
  $taskReport=Get-Item "$taskRoot/Saved/WorkshopQA/$($Mode.ToLower()).json"
  if($taskReport.LastWriteTime -lt $taskStarted){throw 'No fresh workshop report'}
  if(-not (Get-Content $taskReport.FullName -Raw | ConvertFrom-Json).ok){throw 'Workshop check failed; see Saved/WorkshopQA'}
 }
 Write-Output "Workshop $Mode completed"
}finally{if($taskHeld){$taskMutex.ReleaseMutex()};$taskMutex.Dispose()}

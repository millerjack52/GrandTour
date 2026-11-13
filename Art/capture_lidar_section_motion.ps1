param([string]$Label='Motion',[ValidateRange(24,144)][int]$SampleCount=144,[string]$Sequence='/Game/GrandTour/ArtTests/LidarStudy/FirstSection/LS_BankReview',[string[]]$ExtraCommands=@(),[string[]]$StartupArguments=@(),[string]$OutputDirectory='',[string]$PosesPath='')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 $qa="$taskRoot/Saved/LidarAuthoringQA/RS7"
 $motionDir="$qa/$Label"
 if($OutputDirectory){$motionDir=[IO.Path]::GetFullPath($OutputDirectory)}
 New-Item -ItemType Directory -Force -Path $motionDir | Out-Null
 $preset=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
 $motionPoses=$null
 if($Sequence -like '*/LS_PD_Forest' -or $PosesPath){
  # Windows PowerShell emits the JSON array as one pipeline object. Enumerate
  # it before filtering, otherwise bank poses can be selected for forest shots.
  if(-not $PosesPath){$PosesPath="$taskRoot/Saved/LidarAuthoringQA/PerceivedDetail/motion-sequences.json"}
  $sequenceRows=Get-Content $PosesPath -Raw | ConvertFrom-Json
  $matchingSequence=@($sequenceRows | Where-Object {$_.sequence -eq $Sequence})
  if($matchingSequence.Count -ne 1){throw 'Expected one matching camera sequence'}
  $motionPoses=@($matchingSequence[0].poses)
  if(-not $motionPoses){throw 'Missing forest camera poses'}
 }
 $startCommand='BugItGo -47000 -32500 4700 0 35 0'
 if($motionPoses){$pos=$motionPoses[0][1];$startCommand=('BugItGo {0} {1} {2} 0 0 0' -f $pos[0],$pos[1],($pos[2]+100000))}
 $commands=(@($preset.commands)+@($ExtraCommands)+@('EnableCheats',$startCommand,'ke GTCarPawn_0 SetActorHiddenInGame true','ShowHUD','DisableAllScreenMessages','t.IdleWhenNotForeground 0')) -join ','
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12','-MovieSceneCaptureType=/Script/MovieSceneTools.AutomatedLevelSequenceCapture','-LevelSequence=/Game/GrandTour/ArtTests/LidarStudy/FirstSection/LS_BankReview','-MovieFrameRate=24','-MovieFormat=PNG','-MovieWarmUpFrames=96','-MovieDelayBeforeWarmUp=5','-MovieStartFrame=0','-MovieEndFrame=287','-MovieEngineScalabilityMode=0','-MovieCinematicMode=0',('-MovieFolder="'+$qa+'/Motion"'),'-MovieName=bank_{frame}','-MovieOverwriteExisting=1',('-ExecCmds="'+$commands+'"'),('-abslog="'+$taskRoot+'/Saved/Logs/LidarSection-Motion.log"'))
 # Avoid a world-timer delay in the automated capture; warmup frames provide settling.
 $launch=$launch | ForEach-Object {if($_ -like '-LevelSequence=*'){"-LevelSequence=$Sequence"}else{$_ -replace '/Motion"',('/'+$Label+'"')}}
 if($OutputDirectory){$launch=$launch | ForEach-Object {if($_ -like '-MovieFolder=*'){('-MovieFolder="'+$motionDir+'"')}else{$_}}}
 # This machine's legacy frame grabber never writes its queued images. Keep its
 # deterministic sequence clock, but capture the actual viewport with the same
 # HighResShot path as the verified game stills. CSV scheduling also bounds exit.
 $launch=$launch | ForEach-Object {($_ -replace 'MovieDelayBeforeWarmUp=5','MovieDelayBeforeWarmUp=0') -replace '-ExecCmds="','-ExecCmds="CsvProfile FRAMES=480,'}
 $schedule=@()
 # Procedural grass follows the pawn, not the Sequencer camera. Follow the
 # forest camera's XY with the hidden pawn high above it, avoiding wheel contact.
 if($motionPoses){
  for($sample=0;$sample -lt $SampleCount;$sample+=2){
   $seqFrame=2+2*$sample
   for($k=1;$k -lt $motionPoses.Count;$k++){
    if($seqFrame -le $motionPoses[$k][0]){
     $left=$motionPoses[$k-1];$right=$motionPoses[$k]
     $blend=($seqFrame-$left[0])/($right[0]-$left[0])
     $point=@(0,0,0)
     for($axis=0;$axis -lt 3;$axis++){$point[$axis]=$left[1][$axis]+($right[1][$axis]-$left[1][$axis])*$blend}
     $schedule+=('{0}:BugItGo {1} {2} {3} 0 0 0' -f (96+2*$sample),$point[0],$point[1],($point[2]+100000))
     break
    }
   }
  }
 }

 for($i=0;$i -lt $SampleCount;$i++) {$schedule+=('{0}:HighResShot 1600x900 filename="{1}/bank_{2:D4}.png"' -f (98+2*$i),($motionDir.Replace('\','/')),$i)}
 $launch+=@('-LogCmds="LogMovieSceneCapture Verbose"',('-csvExecCmds="'+($schedule -join ',')+'"'),'-ExitAfterCsvProfiling')
 $launch+=@($StartupArguments)
 $motionLog="$taskRoot/Saved/Logs/LidarSection-$Label.log"
 $launch=$launch | ForEach-Object {if($_ -like '-abslog=*'){('-abslog="'+$motionLog+'"')}else{$_}}
 # FCommandLine::MaxCommandLineSize is 16384. A long frame schedule can make
 # Unreal exit before it creates a log; reject that launch with a useful cause.
 if(($launch -join ' ').Length -gt 16000){throw 'Motion capture exceeds the Unreal command-line limit. Reduce SampleCount or use a shorter OutputDirectory.'}
 $captureStartedUtc=[DateTime]::UtcNow
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit()
 for($i=0;$i -lt $SampleCount;$i++){
  $frame=Get-Item -LiteralPath (Join-Path $motionDir ('bank_{0:D4}.png' -f $i)) -ErrorAction SilentlyContinue
  if(-not $frame -or $frame.LastWriteTimeUtc -lt $captureStartedUtc){throw "Missing fresh motion frame $i"}
 }
 $report=if($Label -eq 'Motion'){"$qa/motion-capture.json"}else{"$qa/$Label-capture.json"}
 $shaderFailures=@((Get-Content $motionLog) | Where-Object {$_ -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'})
 @{exit_code=$p.ExitCode;frames=@(Get-ChildItem $motionDir -Filter '*.png').Count;render_validation_passed=($shaderFailures.Count -eq 0);shader_failures=$shaderFailures;log=$motionLog;fps=12;requested_frames=$SampleCount;follows_streaming_pawn=[bool]$motionPoses;sequence_fps=24;sequence=$Sequence;directory=$motionDir;extra_commands=@($ExtraCommands);startup_arguments=@($StartupArguments);quality='saved v6; cinematic scalability disabled';purpose='Rendered motion inspection, not a live frame-rate measurement';method='Actual game viewport screenshots every second sequence frame'} | ConvertTo-Json | Set-Content $report
 if($p.ExitCode -ne 0 -or @(Get-ChildItem $motionDir -Filter '*.png').Count -ne $SampleCount){throw 'Movie capture failed or incomplete'}
 if($shaderFailures.Count -gt 0){throw 'Material fallback invalidates motion capture'}
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

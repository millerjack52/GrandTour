param([ValidateSet('build','capture')][string]$Stage='build')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraMatch'
 $log=$out+'/reference-'+$Stage+'.log';$started=Get-Date
 if($Stage -eq 'build'){
  $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-noshaderworker',('-abslog='+$log),'-ExecutePythonScript=C:/GrandTour/Art/Unreal/build_flora_reference_rig.py')
 }else{
  $camera=(Get-Content ($out+'/reference-rig.json') -Raw|ConvertFrom-Json).camera_name
  $calcam=(Get-Content ($out+'/reference-rig.json') -Raw|ConvertFrom-Json).calibration_camera
  $cmds=@('2:EnableCheats','3:ke GTDistanceStyleController FinishReviewShaders','4:r.SetRes 1024x1024w','5:ke GTDistanceStyleController SetReviewView 1500 -2000 1200 -15.642 126.87 54',('6:viewactor '+$camera),('100:Shot filename="'+$out+'/reference-unreal.png" -nosuffix'),('110:viewactor '+$calcam),('190:Shot filename="'+$out+'/calibration-unreal.png" -nosuffix'))
  $initial='EnableCheats,ShowHUD,DisableAllScreenMessages,r.MotionBlurQuality 0,r.ScreenPercentage 100,r.AntiAliasingMethod 2,r.TemporalAACurrentFrameWeight 0.04,r.DynamicGlobalIlluminationMethod 0,r.DistanceFieldAO 0,r.AmbientOcclusionLevels 0,r.Substrate.RoughDiffuse 0,sg.AntiAliasingQuality,t.IdleWhenNotForeground 0,CsvProfile FRAMES=200'
  $launch=@('C:/GrandTour/GrandTour.uproject','/Game/GrandTour/ArtTests/FloraMatch/L_FloraReferenceRig','-game','-windowed','-ResX=1024','-ResY=1024','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="'+$initial+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($cmds -join ',')+'"'),('-abslog='+$log))
 }
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw ('Unreal exit '+$p.ExitCode)}
 if($Stage -eq 'build'){
  $f=Get-Item ($out+'/reference-rig.json');$report=Get-Content $f.FullName -Raw|ConvertFrom-Json
  if($f.LastWriteTime -lt $started -or -not $report.ok){throw ('Build failed '+$report.error)}
 }else{
  $text=Get-Content -LiteralPath $log -Raw
  $bad=$text -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error|Failed to find an object named'
  $stale=@('reference-unreal.png','calibration-unreal.png' | Where-Object {$f=Get-Item ($out+'/'+$_) -ErrorAction SilentlyContinue;-not $f -or $f.LastWriteTime -lt $started})
  $switches=[regex]::Matches($text,'SURFACE_REVIEW camera').Count
  $ok=-not $bad -and $stale.Count -eq 0 -and $switches -eq 1
  @{ok=$ok;shader_validation_passed=(-not $bad);camera_switches=$switches;performance_verified=$false;started=$started.ToString('o');warmup_frames=94} | ConvertTo-Json | Set-Content ($out+'/reference-capture.json')
  if(-not $ok){throw 'Capture failed'}
 }
 Write-Output ('Flora shader '+$Stage+' passed')
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

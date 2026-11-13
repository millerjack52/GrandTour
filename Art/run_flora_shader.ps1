param([ValidateSet('build','capture')][string]$Stage='build')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraShader'
 $log=$out+'/'+$Stage+'.log';$started=Get-Date
 if($Stage -eq 'build'){
  $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-noshaderworker',('-abslog='+$log),'-ExecutePythonScript=C:/GrandTour/Art/Unreal/refine_flora_shader.py')
 }else{
  $cmds=@('2:EnableCheats','3:ke GTDistanceStyleController FinishReviewShaders','4:r.SetRes 1600x900w','5:ke GTDistanceStyleController SetReviewView 1350 -2000 850 -9.8 124 54',('80:Shot filename="'+$out+'/after-tree.png" -nosuffix'),'90:ke GTDistanceStyleController SetReviewView 350 -1050 110 -7 110 65',('165:Shot filename="'+$out+'/after-understory.png" -nosuffix'),'175:ke GTDistanceStyleController SetReviewView 1450 -1930 850 -9.8 127 54',('250:Shot filename="'+$out+'/after-tree-pan.png" -nosuffix'))
  $initial='EnableCheats,ShowHUD,DisableAllScreenMessages,r.MotionBlurQuality 0,r.ScreenPercentage 100,r.AntiAliasingMethod,sg.AntiAliasingQuality,t.IdleWhenNotForeground 0,CsvProfile FRAMES=265'
  $launch=@('C:/GrandTour/GrandTour.uproject','/Game/GrandTour/ArtTests/FloraPilot/L_FloraPilot','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="'+$initial+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($cmds -join ',')+'"'),('-abslog='+$log))
 }
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw ('Unreal exit '+$p.ExitCode)}
 if($Stage -eq 'build'){
  $f=Get-Item ($out+'/shader-report.json');$report=Get-Content $f.FullName -Raw|ConvertFrom-Json
  if($f.LastWriteTime -lt $started -or -not $report.ok){throw ('Build failed '+$report.error)}
 }else{
  $text=Get-Content -LiteralPath $log -Raw
  $bad=$text -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error|Failed to find an object named'
  $stale=@('after-tree.png','after-understory.png','after-tree-pan.png' | Where-Object {$f=Get-Item ($out+'/'+$_) -ErrorAction SilentlyContinue;-not $f -or $f.LastWriteTime -lt $started})
  $switches=[regex]::Matches($text,'SURFACE_REVIEW camera').Count
  $ok=-not $bad -and $stale.Count -eq 0 -and $switches -eq 3
  @{ok=$ok;shader_validation_passed=(-not $bad);camera_switches=$switches;performance_verified=$false;started=$started.ToString('o');warmup_frames=75} | ConvertTo-Json | Set-Content ($out+'/capture-report.json')
  if(-not $ok){throw 'Capture failed'}
 }
 Write-Output ('Flora shader '+$Stage+' passed')
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

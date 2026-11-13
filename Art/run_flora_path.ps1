param([ValidateSet('build','capture','tune','soften','bark','barktex')][string]$Stage='build')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraPath';$log=$out+'/'+$Stage+'.log';$started=Get-Date
 if($Stage -ne 'capture'){
  $script=if($Stage -eq 'tune'){'tune_flora_path.py'}elseif($Stage -eq 'soften'){'soften_flora_path.py'}elseif($Stage -eq 'bark'){'fix_flora_bark.py'}elseif($Stage -eq 'barktex'){'fix_flora_bark_textures.py'}else{'build_flora_path.py'}
  $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-noshaderworker',('-abslog='+$log),('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script))
 }else{
  $r=Get-Content ($out+'/build-report.json') -Raw|ConvertFrom-Json;if(-not $r.ok){throw 'Build not valid'};$c=$r.camera;$pos=$c.position
  $view=($pos -join ' ')+' '+$c.pitch+' '+$c.yaw+' '+$c.fov
  $near=($pos[0]+65).ToString()+' '+($pos[1]-100).ToString()+' '+($pos[2]+20).ToString()+' '+($c.pitch-7).ToString()+' '+($c.yaw+5).ToString()+' '+$c.fov
  $cmds=@('2:EnableCheats','3:ke GTDistanceStyleController FinishReviewShaders','4:r.SetRes 1600x800w',('5:ke GTDistanceStyleController SetReviewView '+$view),('120:Shot filename="'+$out+'/unreal-path.png" -nosuffix'),('130:ke GTDistanceStyleController SetReviewView '+$near),('240:Shot filename="'+$out+'/unreal-path-near.png" -nosuffix'),('250:ke GTDistanceStyleController SetReviewView '+$view),'260:r.VolumetricFog 0',('360:Shot filename="'+$out+'/unreal-path-no-volumetrics.png" -nosuffix'),'370:r.VolumetricFog 1')
  $initial='EnableCheats,ShowHUD,DisableAllScreenMessages,r.MotionBlurQuality 0,r.ScreenPercentage 100,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64,t.IdleWhenNotForeground 0,CsvProfile FRAMES=400'
  $launch=@('C:/GrandTour/GrandTour.uproject','/Game/GrandTour/ArtTests/FloraPath/L_FloraPath','-game','-windowed','-ResX=1600','-ResY=800','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="'+$initial+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($cmds -join ',')+'"'),('-abslog='+$log))
 }
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw ('Unreal exit '+$p.ExitCode)}
 if($Stage -ne 'capture'){
  $f=Get-Item ($out+'/'+$Stage+'-report.json');$report=Get-Content $f.FullName -Raw|ConvertFrom-Json
  if($f.LastWriteTime -lt $started -or -not $report.ok){throw ('Build failed '+$report.error)}
 }else{
  $text=Get-Content -LiteralPath $log -Raw
  $bad=$text -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error|Failed to find an object named'
  $stale=@('unreal-path.png','unreal-path-near.png','unreal-path-no-volumetrics.png' | Where-Object {$f=Get-Item ($out+'/'+$_) -ErrorAction SilentlyContinue;-not $f -or $f.LastWriteTime -lt $started})
  $switches=[regex]::Matches($text,'SURFACE_REVIEW camera').Count
  $ok=-not $bad -and $stale.Count -eq 0 -and $switches -eq 3
  @{ok=$ok;shader_validation_passed=(-not $bad);camera_switches=$switches;performance_verified=$false;started=$started.ToString('o');warmup_frames=110;resolution=@(1600,800);aa='TSR';volumetric_grid_pixel_size=16;volumetric_grid_z=64} | ConvertTo-Json | Set-Content ($out+'/capture-report.json')
  $csv=Get-ChildItem 'C:/GrandTour/Saved/Profiling/CSV' -Filter '*.csv' | Where-Object {$_.LastWriteTime -ge $started} | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if($csv){Copy-Item -LiteralPath $csv.FullName -Destination ($out+'/capture.csv')}
  if(-not $ok){throw 'Capture failed'}
 }
 Write-Output ('Flora path '+$Stage+' passed')
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

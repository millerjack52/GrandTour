param([ValidateSet('import','capture')][string]$Stage='import')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraPilot'
 $log='C:/GrandTour/Saved/LidarAuthoringQA/AssetIntake/unreal-'+$Stage+'.log'
 if($Stage -eq 'import'){
  $args=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-NullRHI',('-abslog='+$log),'-ExecutePythonScript=C:/GrandTour/Art/Unreal/import_flora_pilot.py')
 }else{
  $cmds=@('2:EnableCheats','3:ke GTDistanceStyleController FinishReviewShaders','4:r.SetRes 1600x900w','5:ke GTDistanceStyleController SetReviewView 1350 -2000 850 -9.8 124 54',('50:Shot filename="'+$out+'/unreal-tree.png" -nosuffix'),'60:ke GTDistanceStyleController SetReviewView 350 -1050 110 -7 110 65',('105:Shot filename="'+$out+'/unreal-understory.png" -nosuffix'))
  $initial='EnableCheats,ShowHUD,DisableAllScreenMessages,r.MotionBlurQuality 0,r.ScreenPercentage 100,t.IdleWhenNotForeground 0,CsvProfile FRAMES=120'
  $args=@('C:/GrandTour/GrandTour.uproject','/Game/GrandTour/ArtTests/FloraPilot/L_FloraPilot','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="'+$initial+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($cmds -join ',')+'"'),('-abslog='+$log))
 }
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit()
 if($p.ExitCode -ne 0){throw ('Unreal failed '+$p.ExitCode)}
 if($Stage -eq 'import'){
  $f=Get-Item ($out+'/unreal-import-report.json');$report=Get-Content $f.FullName -Raw | ConvertFrom-Json
  if($f.LastWriteTime -lt $started -or -not $report.ok){throw ('Import failed '+$report.error)}
 }else{
  $text=Get-Content -LiteralPath $log -Raw
  $bad=$text -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'
  $stale=@('unreal-tree.png','unreal-understory.png' | Where-Object {$f=Get-Item ($out+'/'+$_) -ErrorAction SilentlyContinue;-not $f -or $f.LastWriteTime -lt $started})
  $switches=[regex]::Matches($text,'SURFACE_REVIEW camera').Count
  $ok=-not $bad -and $stale.Count -eq 0 -and $switches -eq 2
  @{ok=$ok;shader_validation_passed=(-not $bad);camera_switches=$switches;performance_verified=$false;started=$started.ToString('o')} | ConvertTo-Json | Set-Content ($out+'/capture-report.json')
  if(-not $ok){throw 'Capture failed'}
 }
 Write-Output ('Flora pilot '+$Stage+' passed')
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}


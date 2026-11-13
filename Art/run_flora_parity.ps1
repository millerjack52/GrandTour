param([ValidateSet('audit','reference','build','candidate','temporal_baseline','temporal_candidate')][string]$Stage='audit')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraParity';New-Item -ItemType Directory -Force $out|Out-Null;$started=Get-Date
 if($Stage -in @('audit','reference')){
  $script=if($Stage -eq 'audit'){'audit_flora_parity.py'}else{'render_flora_parity.py'}
  $launch=@('--background','--factory-startup','--disable-autoexec','--python',('C:/GrandTour/Art/Blender/'+$script))
  $p=Start-Process 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru -RedirectStandardOutput ($out+'/'+$Stage+'.log') -RedirectStandardError ($out+'/'+$Stage+'-stderr.log')
 }else{
  $script='build_flora_parity.py'
  $previousCandidate=$env:GT_FLORA_PARITY_CANDIDATE
  $previousTemporal=$env:GT_FLORA_PARITY_TEMPORAL
  $env:GT_FLORA_PARITY_CANDIDATE=if($Stage -in @('candidate','temporal_candidate')){'1'}else{'0'}
  $env:GT_FLORA_PARITY_TEMPORAL=if($Stage -like 'temporal_*'){'1'}else{'0'}
  $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script),('-abslog='+$out+'/'+$Stage+'.log'))
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
  $env:GT_FLORA_PARITY_CANDIDATE=$previousCandidate
  $env:GT_FLORA_PARITY_TEMPORAL=$previousTemporal
 }
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw ('Parity '+$Stage+' process exited '+$p.ExitCode)}
 $name=if($Stage -eq 'audit'){'source-contract.json'}else{$Stage+'-report.json'}
 $file=Get-Item ($out+'/'+$name);$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if($file.LastWriteTime -lt $started -or -not $r.ok){throw ('Parity '+$Stage+' report failed: '+$r.error)}
 if($Stage -notin @('audit','reference')){
  $log=Get-Content ($out+'/'+$Stage+'.log') -Raw
  if($log -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Parity shader validation failed'}
 }
 Write-Output ('Flora parity '+$Stage+' passed')
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

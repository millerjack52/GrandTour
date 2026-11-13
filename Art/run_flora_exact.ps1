param([ValidateSet('source','build','motion','coverage')][string]$Stage='source')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraParity/AssetMatch';New-Item -ItemType Directory -Force $out|Out-Null;$started=Get-Date
 if($Stage -eq 'source'){
  $p=Start-Process 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -ArgumentList @('--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python','C:/GrandTour/Art/Blender/render_flora_exact.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput ($out+'/source.log') -RedirectStandardError ($out+'/source-stderr.log')
 } else {
  $motionArg=if($Stage -eq 'motion'){'-GTFloraMotion=1'}elseif($Stage -eq 'coverage'){'-GTFloraCoverage=1'}else{'-GTFloraMotion=0'}
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList @('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0',$motionArg,'-ExecutePythonScript=C:/GrandTour/Art/Unreal/build_flora_exact.py',('-abslog='+$out+'/'+$Stage+'.log')) -WindowStyle Hidden -PassThru
 }
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw "Exact $Stage process exited $($p.ExitCode)"}
 $name=if($Stage -eq 'source'){'reference-report.json'}else{$Stage+'-report.json'}
 $file=Get-Item ($out+'/'+$name);$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if($file.LastWriteTime -lt $started -or -not $r.ok){throw "Exact $Stage failed: $($r.error)"}
 if($Stage -ne 'source' -and (Get-Content ($out+'/'+$Stage+'.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Shader validation failed'}
 Write-Output "Exact $Stage passed"
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

param([ValidateSet('bake','bark','scene','audit')][string]$Stage='scene')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraGroup'
 New-Item -ItemType Directory -Force $out | Out-Null
 $started=Get-Date
 if($Stage -in @('bake','bark')){
  $script=if($Stage -eq 'bark'){'bake_flora_group_bark.py'}else{'bake_flora_group.py'}
  $p=Start-Process 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -ArgumentList @('--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',('C:/GrandTour/Art/Blender/'+$script)) -WindowStyle Hidden -PassThru -RedirectStandardOutput ($out+'/'+$Stage+'.log') -RedirectStandardError ($out+'/'+$Stage+'-stderr.log')
 }else{
  $script=if($Stage -eq 'audit'){'audit_flora_group.py'}else{'build_flora_group.py'}
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList @('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script),('-abslog='+$out+'/'+$Stage+'.log')) -WindowStyle Hidden -PassThru
 }
 $null=$p.Handle;$p.WaitForExit()
 @{stage=$Stage;exit_code=$p.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content ($out+'/'+$Stage+'-process.json')
 if($p.ExitCode -ne 0){throw "Flora group $Stage exited $($p.ExitCode)"}
 $file=Get-Item ($out+'/'+$Stage+'-report.json');$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if($file.LastWriteTime -lt $started -or -not $r.ok){throw "Flora group $Stage failed: $($r.error)"}
 if($Stage -in @('scene','audit') -and (Get-Content ($out+'/'+$Stage+'.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Shader validation failed'}
 Write-Output "Flora group $Stage passed"
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

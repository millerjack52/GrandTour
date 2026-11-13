param([ValidateSet('blender34','blender51','unreal')][string]$Stage='blender34')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try{$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 python C:/GrandTour/Art/flora_tree_lightbench_protection.py --prepare
 if($LASTEXITCODE -ne 0){throw 'Protected asset baseline changed'}
 $out='C:/GrandTour/Art/Export/FloraTreeLightBench';New-Item -ItemType Directory -Force $out|Out-Null;$started=Get-Date
 if($Stage -ne 'unreal'){
  $exe=if($Stage -eq 'blender34'){'D:/GrandTourAssets/Tools/blender-3.4.1-windows-x64/blender.exe'}else{'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe'}
  $p=Start-Process $exe -ArgumentList @('--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python','C:/GrandTour/Art/Blender/render_flora_tree_lightbench.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput ($out+'/'+$Stage+'.log') -RedirectStandardError ($out+'/'+$Stage+'-stderr.log')
 }else{
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList @('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-norhithread','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0','-ExecutePythonScript=C:/GrandTour/Art/Unreal/build_flora_tree_lightbench.py',('-abslog='+$out+'/unreal.log')) -WindowStyle Hidden -PassThru
 }
 $null=$p.Handle;$p.WaitForExit()
 @{stage=$Stage;exit_code=$p.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content ($out+'/'+$Stage+'-process.json')
 $f=Get-Item ($out+'/'+$Stage+'/report.json');$r=Get-Content $f.FullName -Raw|ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not $r.ok){throw "Tree light bench $Stage failed: exit $($p.ExitCode) $($r.error)"}
 if($Stage -eq 'unreal' -and (Get-Content ($out+'/unreal.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Shader validation failed'}
 Write-Output "Tree light bench $Stage passed"
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

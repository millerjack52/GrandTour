param([ValidateSet('atmosphere','install_atmosphere','verify_atmosphere')][string]$Stage='atmosphere')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try{
 try{$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/FloraTrail/Atmosphere';New-Item -ItemType Directory -Force $out|Out-Null;$started=Get-Date
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$Stage+'_flora_trail.py'),('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"')
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru;$null=$p.Handle;$p.WaitForExit()
 @{stage=$Stage;exit_code=$p.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content ($out+'/'+$Stage+'-process.json')
 $f=Get-Item ($out+'/'+$Stage+'-report.json');$r=Get-Content $f.FullName -Raw|ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not $r.ok){throw "FloraTrail $Stage failed: exit $($p.ExitCode) $($r.error)"}
 if((Get-Content ($out+'/'+$Stage+'.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Shader validation failed'}
 Write-Output "FloraTrail $Stage passed"
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

param([ValidateSet('audit','before','install','materials','repair','verify','check','coverage','coverageview','longrange')][string]$Stage='audit')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'Unreal slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraIntegration';$started=Get-Date
 $script=if($Stage -eq 'audit'){'audit_lidar_flora.py'}elseif($Stage -eq 'install'){'install_lidar_flora.py'}elseif($Stage -eq 'materials'){'refine_lidar_flora_materials.py'}elseif($Stage -eq 'repair'){'repair_lidar_flora_colliders.py'}elseif($Stage -eq 'verify'){'verify_lidar_flora.py'}else{'check_lidar_flora.py'}
 if($Stage -eq 'coverage'){$script='restore_lidar_flora_coverage.py'}
 $env:GT_FLORA_LIDAR_PHASE=$Stage
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script),('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"')
 if($Stage -in @('audit','install','materials','repair','verify','coverage')){$launch=@($launch|Where-Object {$_ -notin @('-RenderOffScreen','-dx12')})+@('-NullRHI')}
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru;$null=$p.Handle;$p.WaitForExit()
 $file=Get-Item ($out+'/'+$Stage+'-report.json');$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $file.LastWriteTime -lt $started -or -not $r.ok){throw ('LiDAR Flora '+$Stage+' failed: exit '+$p.ExitCode+' '+$r.error)}
 $log=Get-Content ($out+'/'+$Stage+'.log') -Raw
 if($log -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Render validation failed'}
 Write-Output ('LiDAR Flora '+$Stage+' passed')
}finally{Remove-Item Env:GT_FLORA_LIDAR_PHASE -ErrorAction SilentlyContinue;if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

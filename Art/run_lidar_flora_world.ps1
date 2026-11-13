param([ValidateSet('canopy','audit','install','review','refine','polish','verify','grassmaterials')][string]$Stage='audit')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'Unreal slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/LidarStudy/FloraWorld';New-Item -ItemType Directory -Force $out|Out-Null;$started=Get-Date
 $script=if($Stage -eq 'canopy'){'build_lidar_flora_canopy.py'}elseif($Stage -eq 'review'){'review_lidar_flora_world.py'}else{'install_lidar_flora_world.py'}
 $env:GT_FLORA_WORLD_STAGE=$Stage
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=1',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script),('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"')
 if($Stage -in @('audit','install','refine','polish','verify','grassmaterials')){$launch=@($launch|Where-Object {$_ -notin @('-RenderOffScreen','-dx12')})+@('-NullRHI')}
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru;$null=$p.Handle;$p.WaitForExit()
 $file=Get-Item ($out+'/'+$Stage+'-report.json');$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $file.LastWriteTime -lt $started -or -not $r.ok){throw ('Flora world '+$Stage+' failed: exit '+$p.ExitCode+' '+$r.error)}
 $log=Get-Content ($out+'/'+$Stage+'.log') -Raw
 if($log -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Render validation failed'}
 Write-Output ('Flora world '+$Stage+' passed')
}finally{Remove-Item Env:GT_FLORA_WORLD_STAGE -ErrorAction SilentlyContinue;if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

param([ValidateSet('build','audit','shadows','window','check','capture')][string]$Stage='build')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'Unreal slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Renderer already running'}
 $out='C:/GrandTour/Art/Export/FloraDrive';$started=Get-Date;$script=if($Stage -eq 'build'){'build_flora_drive.py'}elseif($Stage -eq 'audit'){'audit_flora_lidar_trial.py'}elseif($Stage -eq 'shadows'){'apply_flora_ground_shadows.py'}elseif($Stage -eq 'window'){'fix_flora_visual_window.py'}elseif($Stage -eq 'capture'){'capture_flora_drive.py'}else{'check_flora_drive.py'}
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script),('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"')
 $launch=if($Stage -in @('build','audit','shadows','window')){@($launch|Where-Object {$_ -notin @('-RenderOffScreen','-dx12')})+@('-NullRHI')}else{$launch}
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru;$null=$p.Handle;$p.WaitForExit()
 $file=Get-Item ($out+'/'+$Stage+'-report.json');$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $file.LastWriteTime -lt $started -or -not $r.ok){throw ('FloraDrive '+$Stage+' failed: exit '+$p.ExitCode+' '+$r.error)}
 $log=Get-Content ($out+'/'+$Stage+'.log') -Raw
 if($log -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Render validation failed'}
 Write-Output ('FloraDrive '+$Stage+' passed')
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

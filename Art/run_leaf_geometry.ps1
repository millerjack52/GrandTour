param([ValidateSet('audit','install')][string]$Stage='audit')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $script=if($Stage -eq 'audit'){'audit_leaf_geometry.py'}else{'install_leaf_geometry.py'}
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-NullRHI',('-abslog=C:/GrandTour/Saved/Logs/LeafGeometry-'+$Stage+'.log'),('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script))
 $started=Get-Date;$p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();$f=Get-Item ('Saved/LidarAuthoringQA/LeafGeometry/'+$Stage+'.json')
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started){throw 'Leaf geometry operation failed'}
 if($Stage -eq 'install' -and -not (Get-Content $f.FullName -Raw|ConvertFrom-Json).ok){throw 'Install validation failed'}
 Write-Output ('Leaf geometry '+$Stage+' finished')
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

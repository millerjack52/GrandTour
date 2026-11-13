$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $started=Get-Date
 $args2=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-NullRHI','-abslog=C:/GrandTour/Saved/Logs/LeafSurface-install.log','-ExecutePythonScript=C:/GrandTour/Art/Unreal/leaf_surface.py')
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args2 -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();$f=Get-Item Saved/LidarAuthoringQA/LeafSurface/install.json;$r=Get-Content $f.FullName -Raw | ConvertFrom-Json
 if(-not $r.ok -or $f.LastWriteTime -lt $started -or $p.ExitCode -ne 0){throw 'Leaf surface install failed'}
 Write-Output 'Leaf surface install passed'
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

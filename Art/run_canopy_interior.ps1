param([ValidateSet('audit','install')][string]$Stage='audit')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $env:GT_CANOPY_INTERIOR_STAGE=$Stage
 $started=Get-Date
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-NullRHI',('-abslog=C:/GrandTour/Saved/Logs/CanopyInterior-'+$Stage+'.log'),'-ExecutePythonScript=C:/GrandTour/Art/Unreal/canopy_interior.py')
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();$f=Get-Item ('Saved/LidarAuthoringQA/CanopyInterior/'+$Stage+'.json')
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not (Get-Content $f.FullName -Raw|ConvertFrom-Json).ok){throw 'Canopy interior operation failed'}
 Write-Output ('Canopy interior '+$Stage+' passed')
} finally {Remove-Item Env:GT_CANOPY_INTERIOR_STAGE -ErrorAction SilentlyContinue;if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

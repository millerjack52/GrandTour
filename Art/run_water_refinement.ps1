param([ValidateSet('audit','install','verify','optics')][string]$Stage='audit')
$ErrorActionPreference='Stop';Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 $env:GT_WATER_REFINEMENT_STAGE=$Stage
 $started=Get-Date
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-NullRHI',('-abslog=C:/GrandTour/Saved/Logs/WaterRefinement-'+$Stage+'.log'),'-ExecutePythonScript=C:/GrandTour/Art/Unreal/refine_lidar_water.py')
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();$f=Get-Item ('Saved/LidarAuthoringQA/WaterRefinement/'+$Stage+'.json')
 @{exit_code=$p.ExitCode;started=$started.ToString('o');report_modified=$f.LastWriteTime.ToString('o');report_ok=(Get-Content $f.FullName -Raw|ConvertFrom-Json).ok} | ConvertTo-Json | Set-Content ('Saved/LidarAuthoringQA/WaterRefinement/'+$Stage+'-process.json')
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not (Get-Content $f.FullName -Raw|ConvertFrom-Json).ok){throw 'Water refinement operation failed'}
 Write-Output ('Water refinement '+$Stage+' passed')
} finally {Remove-Item Env:GT_WATER_REFINEMENT_STAGE -ErrorAction SilentlyContinue;if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

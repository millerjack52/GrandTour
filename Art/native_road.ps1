param([ValidateSet('Install','Check','Finalize')][string]$Mode='Install')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $script=switch($Mode){'Install'{'install_native_road.py'} 'Finalize'{'finalize_native_road.py'} 'Check'{'check_native_road.py'}}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/NativeRoad-'+$Mode+'.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"'))
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 # Retain a process handle before it exits so Windows keeps its exit status.
 $ownedProcessHandle=$p.Handle
 while(-not $p.WaitForExit(5000)){if(((Get-Date)-$started).TotalSeconds -gt 1200){Stop-Process -Id $p.Id;throw 'Owned NativeRoad check exceeded timeout'}}
 $p.WaitForExit()
 $exitStatus=$p.ExitCode
 $f=Get-Item "$taskRoot/Art/Export/NativeRoad/$($Mode.ToLower()).json";$r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
 @{mode=$Mode;exit_code=$exitStatus;started=$started.ToString('o');report_written=$f.LastWriteTime.ToString('o');report_ok=$r.ok;process_id=$p.Id}|ConvertTo-Json|Set-Content "$taskRoot/Art/Export/NativeRoad/$($Mode.ToLower())-process.json"
 if($null -eq $exitStatus -or $exitStatus -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "NativeRoad $Mode failed; inspect fresh report and process status"}
 if((Get-Content "$taskRoot/Saved/Logs/NativeRoad-$Mode.log" -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
 Write-Output "NativeRoad $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

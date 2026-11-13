param([ValidateSet('Inventory','Install','Check')][string]$Mode='Inventory')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $script=if($Mode -eq 'Inventory'){'inspect_benmore_native.py'}elseif($Mode -eq 'Install'){'install_benmore_native.py'}else{'check_benmore_native.py'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"'),('-abslog="'+$taskRoot+'/Saved/Logs/BenmoreNative-'+$Mode+'.log"'))
 if($Mode -eq 'Check'){$taskArgs+=@('-RenderOffScreen','-dx12')}else{$taskArgs+='-NullRHI'}
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 while(-not $p.WaitForExit(5000)){if(((Get-Date)-$started).TotalSeconds -gt 600){Stop-Process -Id $p.Id;throw 'Owned check exceeded ten minutes'}}
 $p.WaitForExit()
 $f=Get-Item "$taskRoot/Art/Export/BenmoreNative/$($Mode.ToLower()).json"
 $r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
 @{exit_code=$p.ExitCode;report_ok=$r.ok;started=$started.ToString('o');written=$f.LastWriteTime.ToString('o')}|ConvertTo-Json|Set-Content "$taskRoot/Art/Export/BenmoreNative/$($Mode.ToLower())-process.json"
 if($p.ExitCode -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "Benmore $Mode failed"}
 Write-Output "Benmore $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

param([ValidateSet('Setup','Check')][string]$Mode='Check')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
$taskOut=Join-Path $PSScriptRoot 'Export/MudRoad/NativeInteractions'
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $taskScript=if($Mode -eq 'Setup'){'setup_native_interactions.py'}else{'check_native_interactions.py'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'),('-abslog="'+$taskRoot+'/Saved/Logs/NativeInteractions-'+$Mode+'.log"'))
 if($Mode -eq 'Setup'){$taskArgs+='-NullRHI'}else{$taskArgs+=@('-RenderOffScreen','-dx12')}
 $started=Get-Date
 $psi=[Diagnostics.ProcessStartInfo]::new('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',($taskArgs -join ' '));$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.WindowStyle='Hidden'
 $proc=[Diagnostics.Process]::Start($psi)
 if(-not $proc.WaitForExit(600000)){Stop-Process -Id $proc.Id;throw 'Owned check exceeded ten minutes'}
 $proc.WaitForExit();$f=Get-Item -LiteralPath (Join-Path $taskOut ($Mode.ToLower()+'-report.json'));$r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
 @{exit_code=$proc.ExitCode;report_ok=$r.ok;started=$started.ToString('o');report_written=$f.LastWriteTime.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskOut ($Mode.ToLower()+'-process.json'))
 if($proc.ExitCode -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "Native interactions $Mode failed"}
 $log=Get-Content -LiteralPath "$taskRoot/Saved/Logs/NativeInteractions-$Mode.log" -Raw
 if($log -match 'Failed to compile Material'){throw 'Shader fallback found'}
 if($Mode -eq 'Check' -and $log -notmatch 'Test Completed\. Result=\{Success\} Name=\{EmitterLuaOracle\}'){throw 'Lua oracle did not pass'}
 Write-Output "Native interactions $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

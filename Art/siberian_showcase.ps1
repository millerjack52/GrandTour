param([ValidateSet('Setup','Check','Tests','Repair','Audit','Treads','Waves','WaveCheck')][string]$Mode='Check')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
$taskOut=Join-Path $PSScriptRoot 'Export/SiberianShowcase'
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $taskScript=if($Mode -eq 'Setup'){'setup_siberian_showcase.py'}elseif($Mode -eq 'Waves'){'install_siberian_waves.py'}elseif($Mode -eq 'Repair'){'repair_siberian_grass_cost.py'}elseif($Mode -eq 'Audit'){'audit_siberian_materials.py'}else{'check_siberian_showcase.py'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$taskScript+'"'),('-abslog="'+$taskRoot+'/Saved/Logs/SiberianShowcase-'+$Mode+'.log"'))
 if($Mode -eq 'Tests') {
  $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ExecCmds="Automation RunTests GrandTour.Showcase+GrandTour.MudRunner+GrandTour.LandscapeMud+GrandTour.Water.RiverReference"','-TestExit="Automation Test Queue Empty"',('-ReportExportPath="'+$taskRoot+'/Saved/Automation/SiberianSurfaces"'),('-abslog="'+$taskRoot+'/Saved/Logs/SiberianShowcase-Tests.log"'))
 } elseif($Mode -in @('Setup','Repair','Audit','Waves')){$taskArgs+='-NullRHI'}else{$taskArgs+=@('-RenderOffScreen','-dx12')}
 if($Mode -eq 'Treads'){$taskArgs+='-GTTreadReview'}
 if($Mode -eq 'WaveCheck'){$taskArgs+='-GTWaveReview'}
 $started=Get-Date
 $taskTelemetry=Join-Path $taskOut ($Mode.ToLower()+'-memory.jsonl')
 [IO.File]::WriteAllText($taskTelemetry,'')
 $psi=[Diagnostics.ProcessStartInfo]::new('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',($taskArgs -join ' '));$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.WindowStyle='Hidden'
 $proc=[Diagnostics.Process]::Start($psi)
 while(-not $proc.WaitForExit(5000)){
  $proc.Refresh();$taskMemory=Get-CimInstance Win32_OperatingSystem
  @{elapsed_s=[math]::Round(((Get-Date)-$started).TotalSeconds,1);private_mb=[math]::Round($proc.PrivateMemorySize64/1MB);resident_mb=[math]::Round($proc.WorkingSet64/1MB);free_physical_mb=[math]::Round($taskMemory.FreePhysicalMemory/1024);free_commit_mb=[math]::Round($taskMemory.FreeVirtualMemory/1024)} | ConvertTo-Json -Compress | Add-Content -LiteralPath $taskTelemetry
  if(((Get-Date)-$started).TotalSeconds -gt 600){Stop-Process -Id $proc.Id;throw 'Owned check exceeded ten minutes'}
 }
 $proc.WaitForExit()
 if($Mode -eq 'Tests') {
  $taskTests=Get-Content -LiteralPath "$taskRoot/Saved/Automation/SiberianSurfaces/index.json" -Raw|ConvertFrom-Json
  if($proc.ExitCode -ne 0 -or $taskTests.failed -gt 0 -or $taskTests.succeeded -lt 1){throw 'Surface regression tests failed'}
  Write-Output "Surface regression tests passed: $($taskTests.succeeded)";return
 }
 $f=Get-Item -LiteralPath (Join-Path $taskOut ($Mode.ToLower()+'-report.json'));$r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
 @{exit_code=$proc.ExitCode;report_ok=$r.ok;started=$started.ToString('o');report_written=$f.LastWriteTime.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskOut ($Mode.ToLower()+'-process.json'))
 if($proc.ExitCode -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "Siberian showcase $Mode failed"}
 if((Get-Content -LiteralPath "$taskRoot/Saved/Logs/SiberianShowcase-$Mode.log" -Raw) -match 'Failed to compile Material'){throw 'Shader fallback found'}
 Write-Output "Siberian showcase $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

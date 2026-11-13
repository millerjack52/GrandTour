param([ValidateSet('Install','Repair','MudRestore','Check','Tests','ForestAudit','ForestInstall','ForestProfile','ForestTune','GrassInstall','GroundStudy','GroundStudyCPU','ShadowBalance','ShadowReview')][string]$Mode='Install')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',('-abslog="'+$taskRoot+'/Saved/Logs/BenmoreWoodland-'+$Mode+'.log"'))
 if($Mode -eq 'Tests'){$taskArgs+=@('-NullRHI','-ExecCmds="Automation RunTests GrandTour.Showcase.SurfaceRegression"','-TestExit="Automation Test Queue Empty"')}
 else {
  $script=switch($Mode){'Install' {'install_benmore_woodland.py'} 'Repair' {'repair_benmore_woodland.py'} 'MudRestore' {'restore_woodland_mud.py'} 'ForestAudit' {'audit_woodland_forest.py'} 'ForestInstall' {'install_woodland_forest.py'} 'ForestProfile' {'profile_woodland_forest.py'} 'ForestTune' {'tune_woodland_forest.py'} 'GrassInstall' {'install_woodland_grass.py'} 'GroundStudy' {'install_woodland_groundstudy.py'} 'GroundStudyCPU' {'check_woodland_groundstudy_cpu.py'} 'ShadowBalance' {'balance_woodland_shadows.py'} 'ShadowReview' {'review_woodland_shadows.py'} default {'check_benmore_woodland.py'}}
  $taskArgs+=('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"')
  if($Mode -in @('Check','ForestProfile','ForestInstall','ShadowReview')){$taskArgs+=@('-RenderOffScreen','-dx12')}else{$taskArgs+='-NullRHI'}
 }
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 while(-not $p.WaitForExit(5000)){if(((Get-Date)-$started).TotalSeconds -gt 900){Stop-Process -Id $p.Id;throw 'Owned check exceeded fifteen minutes'}}
 $p.WaitForExit()
 if($Mode -eq 'Tests') {
  $log=Get-Content "$taskRoot/Saved/Logs/BenmoreWoodland-Tests.log" -Raw
  if($p.ExitCode -ne 0 -or $log -notmatch 'Result=\{Success\}.*SurfaceRegression'){throw 'Woodland regression test failed'}
 } else {
  $f=Get-Item "$taskRoot/Art/Export/BenmoreWoodland/$($Mode.ToLower()).json";$r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
  @{exit_code=$p.ExitCode;report_ok=$r.ok;started=$started.ToString('o');written=$f.LastWriteTime.ToString('o')}|ConvertTo-Json|Set-Content "$taskRoot/Art/Export/BenmoreWoodland/$($Mode.ToLower())-process.json"
  if($p.ExitCode -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "Woodland $Mode failed"}
  if($Mode -in @('Check','ForestProfile','ShadowReview') -and (Get-Content "$taskRoot/Saved/Logs/BenmoreWoodland-$Mode.log" -Raw) -match 'Failed to compile Material|view mode not recognized'){throw 'Woodland material compilation failed; screenshots require review'}
 }
 Write-Output "Woodland $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}





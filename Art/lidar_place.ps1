param([ValidateSet('Prepare','ValidateDesign','ApplyDesign','AuthoringCheck','LoggingCheck','RutWater','RutWaterCheck','TrackDetail','TrackDetailCheck','RiverCheck','RiverDetail','RiverPerf','Profile60','Grass','GrassCheck','TreadCheck','Install','Check','Audit','Polish','WaterDiag','Water','FoliagePerf','FoliageStat')][string]$Mode='Install')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
if($Mode -in @('Prepare','ValidateDesign','ApplyDesign')) {
 $terrainPython=Join-Path $taskRoot 'Saved/Tools/TerrainPython/Scripts/python.exe'
 if(-not (Test-Path -LiteralPath $terrainPython)){throw 'Missing TerrainPython runtime under Saved/Tools'}
 & $terrainPython "$taskRoot/Art/tools/lidar_authoring.py"
 if($LASTEXITCODE -ne 0){throw 'Design validation failed'}
 if($Mode -eq 'ValidateDesign'){return}
 # Prepare to staging; a validation failure cannot leave mixed new/old bake inputs.
 $stage=Join-Path $taskRoot ('Saved/LidarAuthoringPrepare/'+[Guid]::NewGuid().ToString())
 $priorOutput=$env:GT_LIDAR_OUTPUT
 try {
  $env:GT_LIDAR_OUTPUT=$stage
  & $terrainPython "$taskRoot/Art/tools/prepare_lidar_place.py"
  if($LASTEXITCODE -ne 0){throw "Prepare failed; existing inputs kept. Inspect $stage"}
  & $terrainPython "$taskRoot/Art/tools/check_lidar_river.py" $stage
  if($LASTEXITCODE -ne 0){throw "River continuity validation failed; existing inputs kept. Inspect $stage"}
 } finally {$env:GT_LIDAR_OUTPUT=$priorOutput}
 $destination=Join-Path $taskRoot 'Art/Export/LidarStudy/Place'
 $backup=Join-Path $taskRoot ('Saved/LidarAuthoringBackups/Prepare-'+[Guid]::NewGuid().ToString())
 New-Item -ItemType Directory -Path $backup -Force | Out-Null
 foreach($file in Get-ChildItem -LiteralPath $stage -File) {
  $existing=Join-Path $destination $file.Name
  if(Test-Path -LiteralPath $existing){Copy-Item -LiteralPath $existing -Destination $backup}
 }
 foreach($file in Get-ChildItem -LiteralPath $stage -File){Copy-Item -LiteralPath $file.FullName -Destination $destination -Force}
 & $terrainPython "$taskRoot/Art/tools/build_lidar_track_detail.py"
 if($LASTEXITCODE -ne 0){throw 'Track detail preparation failed; saved level unchanged'}
 if($Mode -eq 'Prepare'){Write-Output 'LiDAR inputs prepared; saved level unchanged';return}
 foreach($step in @('Install','Polish','Water','Check')) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Mode $step
  if($LASTEXITCODE -ne 0){throw "ApplyDesign stopped at $step"}
 }
 return
}
& "$PSScriptRoot/wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal slot unavailable; no editor started'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $script=if($Mode -eq 'Grass'){'lidar_grass_gs3.py'}elseif($Mode -eq 'GrassCheck'){'check_lidar_grass_gs3.py'}elseif($Mode -eq 'TreadCheck'){'check_lidar_treads.py'}elseif($Mode -eq 'Profile60'){'profile_lidar_60.py'}elseif($Mode -eq 'RiverPerf'){'diagnose_lidar_river_perf.py'}elseif($Mode -eq 'RiverDetail'){'lidar_river_detail.py'}elseif($Mode -eq 'RiverCheck'){'check_lidar_river.py'}elseif($Mode -eq 'RutWater'){'lidar_rut_water.py'}elseif($Mode -eq 'RutWaterCheck'){'check_lidar_rut_water.py'}elseif($Mode -eq 'TrackDetail'){'lidar_track_detail.py'}elseif($Mode -eq 'TrackDetailCheck'){'check_lidar_track_detail.py'}elseif($Mode -eq 'LoggingCheck'){'check_lidar_logging.py'}elseif($Mode -eq 'AuthoringCheck'){'check_lidar_authoring.py'}elseif($Mode -eq 'Install'){'install_lidar_place.py'}elseif($Mode -eq 'Audit'){'inspect_lidar_assets.py'}elseif($Mode -eq 'Polish'){'polish_lidar_place.py'}elseif($Mode -eq 'WaterDiag'){'diagnose_lidar_water.py'}elseif($Mode -eq 'Water'){'water_lidar_place.py'}elseif($Mode -eq 'FoliagePerf'){'foliage_perf_lidar_place.py'}elseif($Mode -eq 'FoliageStat'){'stat_lidar_place.py'}else{'check_lidar_place.py'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/LidarPlace-'+$Mode+'.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"'))
 if($Mode -eq 'WaterCheck'){$taskArgs+='-GTWaterOnly'}
 if($Mode -eq 'EnrichCheck'){$taskArgs+='-GTEnrichCheck'}
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 # Retain a process handle before it exits so Windows keeps its exit status.
 $ownedProcessHandle=$p.Handle
 $timeoutReported=$false
 while(-not $p.WaitForExit(5000)) {
  if(-not $timeoutReported -and ((Get-Date)-$started).TotalSeconds -gt 2400) {
   Write-Warning "LiDAR $Mode exceeded 2400 seconds. Keeping the reservation and leaving Unreal running; close it normally if needed."
   $timeoutReported=$true
  }
 }
 $p.WaitForExit()
 $exitStatus=$p.ExitCode
 $f=Get-Item "$taskRoot/Art/Export/LidarStudy/Place/$($Mode.ToLower()).json";$r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
 @{mode=$Mode;exit_code=$exitStatus;started=$started.ToString('o');report_written=$f.LastWriteTime.ToString('o');report_ok=$r.ok;process_id=$p.Id}|ConvertTo-Json|Set-Content "$taskRoot/Art/Export/LidarStudy/Place/$($Mode.ToLower())-process.json"
 if($null -eq $exitStatus -or $exitStatus -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "LidarStudy $Mode failed; inspect fresh report and process status"}
 if((Get-Content "$taskRoot/Saved/Logs/LidarPlace-$Mode.log" -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
 Write-Output "LidarStudy $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

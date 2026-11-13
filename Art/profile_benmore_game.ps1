param([switch]$Run, [switch]$CheckOnly,
    [switch]$WaitForSlot,
    [ValidateRange(1,60)][int]$MaxWaitMinutes=30,
    [ValidateRange(60,900)][int]$QuietSeconds=60,
    [ValidateRange(50,100)][int]$ScreenPercentage=100,
    [switch]$AdaptiveResolution,
    [ValidateRange(0,240)][int]$FrameLimit=0,
    [switch]$Lightweight,
    [ValidateRange(1280,3840)][int]$OutputWidth=1600,
    [ValidateRange(720,2160)][int]$OutputHeight=900,
    [switch]$PIE,
    [ValidateSet('willow_visibility','raytracing_instances_lod','motion_blur','tsr_16bit','lumen_cache_updates','lumen_diffuse_off','fleet_far_lod','temporal_aa','contrast_vrs','high_opaque_gi','lumen_irradiance','lumen_async','parked_fleet','authored_tussocks','lumen_gather','tsr_update','nanite_lod','raytracing_vehicle_lod','raytracing_landscape_lod','grass_shadows','receiver_mask','gravel_pom','fine_spray','grass_density')][string[]]$Stages=@(),
    [ValidateSet('Baseline','Driving','Compare','CompareDriving')][string]$Mode='Baseline',
    [ValidateSet('willow_visibility','raytracing_instances_lod','motion_blur','tsr_16bit','lumen_cache_updates','lumen_diffuse_off','fleet_far_lod','temporal_aa','contrast_vrs','high_opaque_gi','lumen_irradiance','lumen_async','parked_fleet','authored_tussocks','tsr_history','screen_percentage','screen_percentage_60','lumen_atlas','nanite_pool','grass_tick','grass_shadows','shadow_coarse','shadow_resolution','lumen_gather','tsr_update','nanite_lod','raytracing_vehicle_lod','landscape_shadow_cache','receiver_mask','gravel_pom','fine_spray','grass_density')][string]$Stage='tsr_history',
    [ValidateRange(15,120)][int]$CaptureSeconds=60,
    [ValidateRange(1,3)][int]$Repeats=3,
    [ValidateSet('Ford','Long_Vista','Lake_Mouth','Vegetation')][string[]]$Views=@('Ford','Long_Vista','Lake_Mouth'))
$ErrorActionPreference='Stop'
if($PIE -and ($OutputWidth -ne 1600 -or $OutputHeight -ne 900)){throw 'Custom output size currently requires standalone mode'}
if($AdaptiveResolution -and $Mode -in @('Compare','CompareDriving')){throw 'Use fixed resolution for isolated A/B comparisons'}
if($Stages.Count -and $Mode -notin @('Compare','CompareDriving')){throw 'Multiple stages require a comparison mode'}
$root=Split-Path $PSScriptRoot
$reviewPause=Join-Path $root 'Saved/Profiling/benmore-review-pause.txt'
if($Run -and (Test-Path -LiteralPath $reviewPause)){throw ('Capture paused for review: '+(Get-Content -LiteralPath $reviewPause -Raw))}
function Get-ExternalLoad([int]$OwnedEditorId=0) {
    Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $OwnedEditorId -and (
            $_.Name -match '^(UnrealEditor.*|GrandTour.*|GoWR|GoW|Ace7Game|FarCry6|blender|MSBuild|ShaderCompileWorker|cl|link)\.exe$' -or
            $_.ExecutablePath -match '\\steamapps\\common\\' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'bash.exe' -and $_.CommandLine -match 'Art/(suite|build)\.sh')
        )
    } | Select-Object Name,ProcessId,ExecutablePath
}
if(-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)){throw 'GPU telemetry unavailable; nothing launched.'}
if($CheckOnly){
    $blocked=@(Get-ExternalLoad)
    if($blocked.Count){$blocked | Format-Table -AutoSize; throw 'Occupied Unreal/build slot or external workload. Nothing launched or closed.'}
    Write-Output 'Process preflight clear. A quiet GPU and exclusive window still need verification before -Run.'; return
}
if(-not $Run){throw 'Use -CheckOnly for a read-only process check. Use -Run only in the agreed exclusive profiling window.'}
# wait_unreal_free.ps1 also checks this reservation. Holding it while an
# existing test finishes prevents cooperative launchers taking the gap before
# our quiet-GPU preflight. Direct launchers still need the process guards.
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$held=$false
$reservationDeadline=[DateTime]::UtcNow.AddMinutes($MaxWaitMinutes)
try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
if(-not $held -and $WaitForSlot){
    Write-Output 'Waiting for the existing guarded operation to release the Unreal slot.'
    while(-not $held -and [DateTime]::UtcNow -lt $reservationDeadline){
        try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
}
if(-not $held){$mutex.Dispose();throw 'Another guarded operation owns the slot.'}
$oldOutput=$env:GT_BENMORE_PROFILE_OUT
$oldOptions=$env:GT_BENMORE_PROFILE_OPTIONS
try {
$slotDeadline=[DateTime]::UtcNow.AddMinutes($MaxWaitMinutes)
$blocked=@(Get-ExternalLoad)
if($blocked.Count -and -not $WaitForSlot){$blocked | Format-Table -AutoSize; throw 'Occupied Unreal/build slot or external workload. Nothing launched or closed.'}
if($blocked.Count){Write-Output 'Profiling slot reserved; waiting for existing workloads to finish. No process will be closed.'}
while($blocked.Count){
    if([DateTime]::UtcNow -ge $slotDeadline){throw 'Timed out waiting for the reserved profiling slot; nothing launched or closed.'}
    Start-Sleep -Seconds 5
    $blocked=@(Get-ExternalLoad)
}
$runId=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$out=Join-Path $root ('Art/Export/BenmoreGaea/PerformanceRuns/'+$runId)
New-Item -ItemType Directory -Path $out | Out-Null
$invalid=Join-Path $out 'external-load-invalid.json'
$gpuLog=Join-Path $out 'gpu-telemetry.csv'
# Do not profile while another unidentified GPU client saturates the adapter.
# This is a quiet-start check, not a universal game detector or thermal guarantee.
$quietSamples=[int][Math]::Ceiling($QuietSeconds/5.0)
$quietCount=0
Write-Output ('Waiting for {0} uninterrupted quiet seconds before launching the game.' -f $QuietSeconds)
while($quietCount -lt $quietSamples){
    if([DateTime]::UtcNow -ge $slotDeadline){throw 'Quiet window did not become available before the deadline. Nothing launched or closed.'}
    $gpu=@(nvidia-smi --query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu,temperature.gpu,pstate,clocks.gr,power.draw --format=csv,noheader,nounits)
    if($LASTEXITCODE -ne 0 -or $gpu.Count -ne 1){throw 'Cannot verify the profiling GPU; nothing launched.'}
    Add-Content -LiteralPath $gpuLog -Value $gpu
    $util=[double]::Parse(($gpu[0].Split(',')[4]).Trim(),[Globalization.CultureInfo]::InvariantCulture)
    $clock=[double]::Parse(($gpu[0].Split(',')[7]).Trim(),[Globalization.CultureInfo]::InvariantCulture)
    $watts=[double]::Parse(($gpu[0].Split(',')[8]).Trim(),[Globalization.CultureInfo]::InvariantCulture)
    # Desktop composition can show 10-20% at the 210 MHz idle clock. Treat
    # utilization with clocks/power, rather than mistaking that for a loaded GPU.
    $activeLoad=@(Get-ExternalLoad)
    $busyGPU=$util -gt 10 -and ($clock -gt 500 -or $watts -gt 15)
    if($activeLoad.Count -or $busyGPU){
        if(-not $WaitForSlot){throw 'External work interrupted the quiet preflight. Nothing launched or closed.'}
        $quietCount=0
    }else{$quietCount++}
    Start-Sleep -Seconds 5
}
if(@(Get-ExternalLoad).Count){throw 'Workload started during preflight. Nothing launched.'}
$inputs=@(Get-ChildItem -LiteralPath (Join-Path $root 'Source'),(Join-Path $root 'Config') -File -Recurse)
$inputs+=Get-Item -LiteralPath (Join-Path $root 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'),$PSCommandPath,(Join-Path $root 'Art/Unreal/profile_benmore_game.py'),(Join-Path $root 'Art/Unreal/benmore_profile_drive.py'),(Join-Path $root 'Art/Unreal/benmore_render_controls.py'),(Join-Path $root 'Art/tools/benmore_profile_metrics.py')
if($PIE){$inputs+=Get-Item -LiteralPath (Join-Path $root 'Art/Unreal/profile_benmore_play.py')}
$inputs+=Get-ChildItem -LiteralPath (Join-Path $root 'Binaries/Win64') -Filter 'UnrealEditor-GrandTour*.dll' -File
$hashes=@($inputs | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash)
# Detect ordinary shared-project asset edits without loading assets or hashing
# gigabytes during a timed run. This metadata inventory is not a content backup.
function Get-ContentInventory {
    @(Get-ChildItem -LiteralPath (Join-Path $root 'Content') -Recurse -File |
        Where-Object {$_.Extension -in '.uasset','.umap'} |
        Sort-Object FullName | ForEach-Object {
            '{0}|{1}|{2}' -f $_.FullName,$_.Length,$_.LastWriteTimeUtc.Ticks
        })
}
$contentBefore=Get-ContentInventory
@{utc=[DateTime]::UtcNow.ToString('o');scope='Uncooked standalone game capture; see report for stationary/driving scope';inputs=$hashes;content_metadata=$contentBefore;head=(& git -C $root rev-parse HEAD);status=@(& git -C $root status --short)} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'manifest.json') -Encoding utf8
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv | Set-Content -LiteralPath (Join-Path $out 'gpu-clients-before.csv')
$env:GT_BENMORE_PROFILE_OUT=$out
$env:GT_BENMORE_PROFILE_OPTIONS=@{mode=$Mode;output_width=$OutputWidth;output_height=$OutputHeight;stage=$Stage;stages=@($Stages);seconds=$CaptureSeconds;repeats=$Repeats;views=@($Views);screen_percentage=$ScreenPercentage;adaptive=[bool]$AdaptiveResolution;frame_limit=$FrameLimit;lightweight=[bool]$Lightweight;pie=[bool]$PIE} | ConvertTo-Json -Compress
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview','-game','-windowed','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-GTNoLoad','-csvGpuStats','-trace=default,gpu',('-ResX='+$OutputWidth),('-ResY='+$OutputHeight),'-ForceRes',('-ExecCmds="t.MaxFPS 0,r.VSync 0,py '+$root+'/Art/Unreal/profile_benmore_game.py"'),('-tracefile="'+$out+'/timing.utrace"'),('-abslog="'+$out+'/editor.log"'))
if($Lightweight){$argsList=@($argsList | Where-Object {$_ -ne '-csvGpuStats' -and $_ -notlike '-trace*'})}
if($PIE){
    $argsList=@($argsList | Where-Object {$_ -ne '-game' -and $_ -notlike '-ExecCmds=*'})
    $argsList+=('-ExecutePythonScript="'+$root+'/Art/Unreal/profile_benmore_play.py"')
    $argsList+='-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False'
}
$started=Get-Date
if(@(Get-ExternalLoad).Count){throw 'Workload started before launch. Nothing launched.'}
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
while(-not $p.HasExited){
    if(((Get-Date)-$started).TotalMinutes -gt 45){
        $p.CloseMainWindow() | Out-Null
        throw 'Owned game capture exceeded 45 minutes; requested graceful closure. Verify it exited before another launch.'
    }
    $load=@(Get-ExternalLoad -OwnedEditorId $p.Id | Where-Object {$_.Name -ne 'ShaderCompileWorker.exe'})
    if($load){$load | ConvertTo-Json | Set-Content -LiteralPath $invalid -Encoding utf8}
    nvidia-smi --query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu,temperature.gpu,pstate,clocks.gr,power.draw --format=csv,noheader,nounits | Add-Content -LiteralPath $gpuLog
    if($LASTEXITCODE -ne 0){@{error='GPU telemetry lost'} | ConvertTo-Json | Set-Content -LiteralPath $invalid -Encoding utf8}
    Start-Sleep -Seconds 5
    $p.Refresh()
}
$changed=@($hashes | Where-Object {-not (Test-Path -LiteralPath $_.Path) -or (Get-FileHash -LiteralPath $_.Path -Algorithm SHA256).Hash -ne $_.Hash})
if($changed){
    $sourcePrefix=(Join-Path $root 'Source')+'\'
    $runtimeChanges=@($changed | Where-Object {-not $_.Path.StartsWith($sourcePrefix,[StringComparison]::OrdinalIgnoreCase)})
    if($runtimeChanges.Count){$changed | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'changed-inputs.json');throw 'Runtime inputs changed during run; comparison invalid.'}
    # Source editing cannot replace code already loaded from the fingerprinted
    # DLL. Builds remain forbidden during the capture. Preserve traceability,
    # and require new validation after those edits are compiled.
    @{note='Unbuilt source edits only. Captured DLLs/configuration/helpers unchanged; this result applies to those binaries, not the next build.';changes=$changed} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'source-edits-during-run.json')
}
$contentChanged=@(Compare-Object -ReferenceObject $contentBefore -DifferenceObject (Get-ContentInventory))
if($contentChanged){$contentChanged | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'changed-content.json');throw 'Content assets changed during run; comparison invalid.'}
if(Test-Path -LiteralPath $invalid){throw 'External workload or telemetry failure invalidated this run.'}
$file=Get-Item -LiteralPath (Join-Path $out 'profile-report.json')
if($file.LastWriteTime -lt $started){throw 'No fresh profile report'}
$report=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'BENMORE_GAME_PROFILE_OK; inspect frame-time, memory, route and visual gates'
} finally {
    $env:GT_BENMORE_PROFILE_OUT=$oldOutput
    $env:GT_BENMORE_PROFILE_OPTIONS=$oldOptions
    $mutex.ReleaseMutex();$mutex.Dispose()
}

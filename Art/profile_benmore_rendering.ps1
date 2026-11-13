param([switch]$Run, [switch]$CheckOnly,
    [switch]$WaitForSlot,
    [ValidateRange(1,60)][int]$MaxWaitMinutes=30,
    [ValidateSet('Baseline','Isolation','Memory','Candidate')][string]$Mode='Baseline',
    [ValidateSet('foliage_far_lod','foliage_lod2_segments','foliage_nanite','foliage_nanite_plain','foliage_nanite_volume','foliage_nanite_willows','foliage_vertex_colour','lumen_lighting_updates','lumen_card_capture_budget','spray_sparse_updates')][string]$Stage='foliage_far_lod',
    [ValidateRange(0.001,0.024)][double]$FarLODScreenSize=0.008,
    [ValidateSet('shadow_pool','nanite_pool','tsr_history','lumen_hardware_raytracing')][string]$MemoryProbe='shadow_pool',
    [ValidateRange(0,8192)][int]$MemoryReference=0,
    [switch]$DisableEditorViewportRealtime,
    [ValidateRange(15,120)][int]$CaptureSeconds=60,
    [ValidateRange(1,3)][int]$Repeats=3,
    [ValidateSet('Ford','Long_Vista','Lake_Mouth')][string[]]$Views=@('Ford','Long_Vista','Lake_Mouth'),
    [ValidateSet('water','landscape_grass','vegetation_meshes','shadows','composition_tussocks','composition_shrubs','shrub_shadows','lumen_gi','lumen_reflections','clouds')]
    [string[]]$Features=@('water','landscape_grass','vegetation_meshes','shadows'))
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
function Get-ExternalLoad([int]$OwnedEditorId=0) {
    Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $OwnedEditorId -and (
            $_.Name -match '^(UnrealEditor.*|GrandTour.*|GoWR|GoW|Ace7Game|FarCry6|blender|MSBuild|ShaderCompileWorker|cl|link)\.exe$' -or
            $_.ExecutablePath -match '\\steamapps\\common\\' -or
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
if(-not $mutex.WaitOne(0)){$mutex.Dispose();throw 'Another profiling runner owns the slot.'}
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
for($sample=0;$sample -lt 12;$sample++){
    $gpu=@(nvidia-smi --query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu,temperature.gpu,pstate,clocks.gr,power.draw --format=csv,noheader,nounits)
    if($LASTEXITCODE -ne 0 -or $gpu.Count -ne 1){throw 'Cannot verify the profiling GPU; nothing launched.'}
    Add-Content -LiteralPath $gpuLog -Value $gpu
    $util=[double]::Parse(($gpu[0].Split(',')[4]).Trim(),[Globalization.CultureInfo]::InvariantCulture)
    $clock=[double]::Parse(($gpu[0].Split(',')[7]).Trim(),[Globalization.CultureInfo]::InvariantCulture)
    $watts=[double]::Parse(($gpu[0].Split(',')[8]).Trim(),[Globalization.CultureInfo]::InvariantCulture)
    # Desktop composition can show 10-20% at the 210 MHz idle clock. Treat
    # utilization with clocks/power, rather than mistaking that for a loaded GPU.
    if($util -gt 10 -and ($clock -gt 500 -or $watts -gt 15)){throw 'GPU has active external load. Nothing launched; retry in the reserved window.'}
    Start-Sleep -Seconds 5
}
if(@(Get-ExternalLoad).Count){throw 'Workload started during preflight. Nothing launched.'}
$inputs=@(Get-ChildItem -LiteralPath (Join-Path $root 'Source'),(Join-Path $root 'Config') -File -Recurse)
$inputs+=Get-Item -LiteralPath (Join-Path $root 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'),$PSCommandPath,(Join-Path $root 'Art/Unreal/profile_benmore_rendering.py'),(Join-Path $root 'Art/tools/benmore_profile_metrics.py')
$inputs+=Get-ChildItem -LiteralPath (Join-Path $root 'Binaries/Win64') -Filter 'UnrealEditor-GrandTour*.dll' -File
if($Mode -eq 'Candidate'){
    $inputs+=Get-Item -LiteralPath (Join-Path $root 'Art/Unreal/benmore_performance_stages.py'),(Join-Path $root 'Art/Unreal/benmore_far_tussock_trial.py'),(Join-Path $root 'Art/Unreal/benmore_foliage_detail_trial.py'),(Join-Path $root 'Art/Unreal/benmore_painterly_surface.py')
    if($Stage -eq 'foliage_far_lod'){
        $inputs+=Get-ChildItem -LiteralPath (Join-Path $root 'Art/Export/BenmoreGaea/FarTussockTrial_20261010_v2') -File | Where-Object {$_.Extension -in '.json','.fbx'}
    }
    if($Stage -eq 'foliage_lod2_segments'){
        $inputs+=Get-Item -LiteralPath (Join-Path $root 'Art/Unreal/benmore_tussock_segments_trial.py')
        $inputs+=Get-ChildItem -LiteralPath (Join-Path $root 'Art/Export/BenmoreGaea/TussockSegments_20261011T023511Z') -File | Where-Object {$_.Extension -in '.json','.fbx'}
    }
}
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
@{utc=[DateTime]::UtcNow.ToString('o');scope='Stationary renderer isolation; no driving or full-baseline claim';inputs=$hashes;content_metadata=$contentBefore;head=(& git -C $root rev-parse HEAD);status=@(& git -C $root status --short)} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'manifest.json') -Encoding utf8
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv | Set-Content -LiteralPath (Join-Path $out 'gpu-clients-before.csv')
$env:GT_BENMORE_PROFILE_OUT=$out
$env:GT_BENMORE_PROFILE_OPTIONS=@{mode=$Mode;stage=$Stage;far_lod_screen=$FarLODScreenSize;memory_probe=$MemoryProbe;memory_reference=$MemoryReference;disable_editor_viewport_realtime=[bool]$DisableEditorViewportRealtime;seconds=$CaptureSeconds;repeats=$Repeats;views=@($Views);features=@($Features)} | ConvertTo-Json -Compress
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-csvGpuStats','-trace=default,gpu','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-tracefile="'+$out+'/timing.utrace"'),('-ExecutePythonScript="'+$root+'/Art/Unreal/profile_benmore_rendering.py"'),('-abslog="'+$out+'/editor.log"'))
$started=Get-Date
if(@(Get-ExternalLoad).Count){throw 'Workload started before launch. Nothing launched.'}
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
while(-not $p.HasExited){
    $load=@(Get-ExternalLoad -OwnedEditorId $p.Id | Where-Object {$_.Name -ne 'ShaderCompileWorker.exe'})
    if($load){$load | ConvertTo-Json | Set-Content -LiteralPath $invalid -Encoding utf8}
    nvidia-smi --query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu,temperature.gpu,pstate,clocks.gr,power.draw --format=csv,noheader,nounits | Add-Content -LiteralPath $gpuLog
    if($LASTEXITCODE -ne 0){@{error='GPU telemetry lost'} | ConvertTo-Json | Set-Content -LiteralPath $invalid -Encoding utf8}
    Start-Sleep -Seconds 5
    $p.Refresh()
}
$changed=@($hashes | Where-Object {-not (Test-Path -LiteralPath $_.Path) -or (Get-FileHash -LiteralPath $_.Path -Algorithm SHA256).Hash -ne $_.Hash})
if($changed){$changed | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'changed-inputs.json');throw 'Inputs changed during run; comparison invalid.'}
$contentChanged=@(Compare-Object -ReferenceObject $contentBefore -DifferenceObject (Get-ContentInventory))
if($contentChanged){$contentChanged | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'changed-content.json');throw 'Content assets changed during run; comparison invalid.'}
if(Test-Path -LiteralPath $invalid){throw 'External workload or telemetry failure invalidated this run.'}
$file=Get-Item -LiteralPath (Join-Path $out 'profile-report.json')
if($file.LastWriteTime -lt $started){throw 'No fresh profile report'}
$report=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'BENMORE_PROFILE_OK; review stationary per-pass CSVs, not a driving FPS guarantee'
} finally {
    $env:GT_BENMORE_PROFILE_OUT=$oldOutput
    $env:GT_BENMORE_PROFILE_OPTIONS=$oldOptions
    $mutex.ReleaseMutex();$mutex.Dispose()
}

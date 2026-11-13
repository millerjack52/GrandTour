<#
Leg dressing LD8a step 4 (docs/LEG_DRESSING_PLAN.md LD8a): the GPU profile of The Hide's dressing, dressing on and off.
Per pair: hide_shots with -GTLookDressing=0, then =1 (ProfileGPU after hide_11_track, hide_17_border_low, hide_21_rut_wet,
hide_29_ford_shallow), then the biome views alone (-GTShotsFrom=53: view_forest and view_thicket, each on and dress0).
Every run is -game -RenderOffScreen -GTProfileGPU; the runner holds after each profiled picture until the shader and asset
compilers are empty, then runs ProfileGPU (FGTM6TestRunner::TickProfile). Before each run the GPU cool-down guard waits
until nvidia-smi reads -CoolC or less (at most -MaxWaitMin minutes; LandscapeToolkit.md "thermal throttling voids perf
runs"). Logs: Saved/Logs/ld8_<run>.log. The last pair's dressing-on pictures (overview, track, forest, thicket, hilltop)
are copied to Saved/Screenshots/LD8a. Then: python Art/dressing/ld8_profile.py (the tables). Close the editor first.
  powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\ld8_profile.ps1 [-Pairs 3] [-StartPair 1] [-CoolC 62] [-Only hide|views]
Runs append to docs/landscape_migration/ld8_profile_runs.json (delete it for a fresh series).
#>
param(
    [int]$Pairs = 3,
    [int]$CoolC = 62,
    [int]$MaxWaitMin = 10,
    [int]$Captures = 1,
    [string]$Only = '',
    [int]$StartPair = 1,
    [int]$IdleUtil = 60,
    # LD8b: -Series lean = 2 views runs, then hide_shots dressing off and on (4 launches); -Proceed runs anyway after
    # -MaxWaitMin (the temperature is recorded); -Tag names the logs, the runs file and the picture folder.
    [string]$Series = 'pairs',
    [string]$Tag = 'ld8',
    [switch]$Proceed
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Ue = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Uproject = Join-Path $Root 'GrandTour.uproject'
$Logs = Join-Path $Root 'Saved\Logs'
$Shots = Join-Path $Root 'Saved\Screenshots\M6'
$Out = Join-Path (Join-Path $Root 'Saved\Screenshots') $(if ($Tag -eq 'ld8') { 'LD8a' } else { $Tag.ToUpper() })
$RunsJson = Join-Path $Root "docs\landscape_migration\$($Tag)_profile_runs.json"

function Say([string]$Message) { Write-Host ('LD8_PROFILE ' + $Message) }
function Gpu() {
    $t = & nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active,clocks.gr,utilization.gpu --format=csv,noheader,nounits
    $p = ($t -split ',') | ForEach-Object { $_.Trim() }
    return @{ temp = [int]$p[0]; reasons = $p[1]; clock = [int]$p[2]; util = [int]$p[3] }
}
function CoolDown() {
    # Cool (-CoolC) AND idle: another program on the GPU (2026-09-28: a game started mid-series) voids a run, so wait
    # for three samples in a row at -CoolC or less and utilization at -IdleUtil % or less (the desktop alone reads
    # 25-45 % in bursts; a game reads 90-100 %), at most -MaxWaitMin; a run that never gets them is skipped.
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $idle = 0
    $g = Gpu
    while ($clock.Elapsed.TotalMinutes -lt $MaxWaitMin) {
        if ($g.temp -le $CoolC -and $g.util -le $IdleUtil) { $idle++ } else { $idle = 0 }
        if ($idle -ge 3) { break }
        Start-Sleep -Seconds 10
        $g = Gpu
    }
    return @{ temp = $g.temp; reasons = $g.reasons; util = $g.util; waited_s = [int]$clock.Elapsed.TotalSeconds; cool = ($idle -ge 3) }
}

$running = @(Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'" | Where-Object { $_.CommandLine -like '*GrandTour.uproject*' })
if ($running.Count -gt 0) { Say ('refused: a GrandTour editor is running (pid ' + (($running | ForEach-Object { $_.ProcessId }) -join ',') + ')'); exit 2 }

$runs = New-Object System.Collections.ArrayList
if (Test-Path $RunsJson) { try { foreach ($r in (Get-Content $RunsJson -Raw | ConvertFrom-Json)) { [void]$runs.Add($r) } } catch { } }
New-Item -ItemType Directory -Force $Out | Out-Null
for ($pair = $StartPair; $pair -le $Pairs; $pair++) {
    if ($Series -eq 'pair') {
        # LD8c: one hide_shots run dressing off, one on; the on run goes on into the biome views (-GTShotsThenViews), so
        # its pictures are the six dressing-on ones and nothing later overwrites them.
        if ($pair -gt $StartPair) { break }
        $plan = @(
            @{ name = 'hide_d0'; args = @('-GTLookDressing=0', '-GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud'); kind = 'hide' },
            @{ name = 'hide_d1'; args = @('-GTLookDressing=1', '-GTShotsThenViews', '-GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud'); kind = 'hide';
               pics = @('hide_5_overview', 'hide_11_track', 'view_forest_on', 'view_thicket_on', 'view_hilltop_on', 'view_ford_on') })
    } elseif ($Series -eq 'lean') {
        if ($pair -gt $StartPair) { break }
        $plan = @(
            @{ name = 'views_1'; args = @('-GTShotsFrom=53'); kind = 'views' },
            @{ name = 'views_2'; args = @('-GTShotsFrom=53'); kind = 'views'; pics = @('view_forest_on', 'view_thicket_on', 'view_hilltop_on', 'view_ford_on') },
            @{ name = 'hide_d0'; args = @('-GTLookDressing=0', '-GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud'); kind = 'hide' },
            @{ name = 'hide_d1'; args = @('-GTLookDressing=1', '-GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud'); kind = 'hide'; pics = @('hide_5_overview', 'hide_11_track') })
    } else {
    $plan = @(
        @{ name = "hide_d0_p$pair"; args = @('-GTLookDressing=0', '-GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud'); kind = 'hide' },
        @{ name = "hide_d1_p$pair"; args = @('-GTLookDressing=1', '-GTProbeMaterial=/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud'); kind = 'hide' },
        @{ name = "views_p$pair"; args = @('-GTShotsFrom=53'); kind = 'views' })
    }
    foreach ($run in $plan) {
        if ($Only -and $run.kind -ne $Only) { continue }
        $cool = CoolDown
        Say ("{0}: GPU {1} C, {2} % busy after {3} s wait (reasons {4})" -f $run.name, $cool.temp, $cool.util, $cool.waited_s, $cool.reasons)
        if (-not $cool.cool -and -not $Proceed) {
            Say ("{0}: SKIPPED - the GPU was not cool and idle within {1} min (another program on it?)" -f $run.name, $MaxWaitMin)
            continue
        }
        $log = "$($Tag)_$($run.name).log"
        $argsList = @($Uproject, '/Game/GrandTour/Legs/L_Leg03', '-game', '-RenderOffScreen', '-unattended', '-nopause', '-nosplash', '-nosound',
            "-log=$log", '-GTHideShots', '-GTNoLoad', '-GTProfileGPU', "-GTProfileCaptures=$Captures") + $run.args
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $p = Start-Process -FilePath $Ue -ArgumentList $argsList -NoNewWindow -PassThru -Wait
        $secs = [int]$sw.Elapsed.TotalSeconds
        Start-Sleep -Seconds 5
        $after = Gpu
        $logPath = Join-Path $Logs $log
        $result = ''
        if (Test-Path $logPath) { $result = (Select-String -Path $logPath -Pattern 'GTDRIVETEST_RESULT' | Select-Object -Last 1).Line }
        if ($result.Length -gt 160) { $result = $result.Substring(0, 160) }
        Say ("{0}: exit {1} in {2} s, GPU {3} C after; {4}" -f $run.name, $p.ExitCode, $secs, $after.temp, $result)
        [void]$runs.Add([pscustomobject]@{ name = $run.name; pair = $pair; kind = $run.kind; log = $log; exit = $p.ExitCode; seconds = $secs;
            gpu_before_c = $cool.temp; waited_s = $cool.waited_s; cooled = $cool.cool; reasons_before = $cool.reasons;
            gpu_after_c = $after.temp; reasons_after = $after.reasons; util_after = $after.util; result = $result; finished = (Get-Date -Format 's') })
        if ($after.util -gt $IdleUtil) { Say ("{0}: WARNING - the GPU is {1} % busy 5 s after the run: another program shares it" -f $run.name, $after.util) }
        ConvertTo-Json -InputObject @($runs) -Depth 4 | Set-Content -Encoding utf8 $RunsJson
        if ($run.pics) {
            foreach ($n in $run.pics) { Copy-Item (Join-Path $Shots "$n.png") (Join-Path $Out "$n.png") -Force }
        }
        if ($Series -ne 'lean' -and $pair -eq $Pairs -and $run.name -like 'hide_d1_*') {
            foreach ($n in 'hide_5_overview', 'hide_11_track') { Copy-Item (Join-Path $Shots "$n.png") (Join-Path $Out "$n.png") -Force }
        }
        if ($Series -ne 'lean' -and $pair -eq $Pairs -and $run.kind -eq 'views') {
            foreach ($n in 'view_forest_on', 'view_thicket_on', 'view_hilltop_on') { Copy-Item (Join-Path $Shots "$n.png") (Join-Path $Out "$n.png") -Force }
        }
    }
}
Say "done: $RunsJson"

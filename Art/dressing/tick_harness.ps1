<#
Stage C step 4 (docs/LandscapeMigrationManifest.md 9.C.4): the ticking-editor pass. PCG generation and landscape
edit-layer merges do nothing in a commandlet, so this runs a task script inside the full editor:
  1. writes Content/Python/init_unreal.py, a bootstrap that does nothing unless env GT_TOOLKIT_HARNESS names an
     existing task script (a stray copy stays inert);
  2. starts UnrealEditor.exe on the map, with GT_TOOLKIT_HARNESS set for that child process only;
  3. waits up to -TimeoutMinutes (25), then kills the editor tree. It also kills it when the task report says
     "finished" but the editor is still up -QuitGraceSeconds later (a prompt on quit, say);
  4. in a finally, whatever happened, deletes the bootstrap (and Content/Python if this script created it) and
     checks that it is gone.
The editor window appears on screen while this runs; the first open compiles many shaders. Close the editor first.
  powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\tick_harness.ps1 [-Task <abs .py>] [-TimeoutMinutes 25]
The task writes <task>_report.json next to itself; gate on that. Exit code: 0 report ok, 1 report not ok or missing,
2 refused to start.
#>
param(
    [string]$Task = (Join-Path $PSScriptRoot 'tick_apply_and_generate.py'),
    [string]$Map = '/Game/GrandTour/Test/L_OWToolkitTest',
    [int]$TimeoutMinutes = 25,
    [int]$QuitGraceSeconds = 180
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Uproject = Join-Path $Root 'GrandTour.uproject'
$Editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$PyDir = Join-Path $Root 'Content\Python'
$Boot = Join-Path $PyDir 'init_unreal.py'
$Task = (Resolve-Path $Task).Path
$Report = Join-Path (Split-Path $Task) ([IO.Path]::GetFileNameWithoutExtension($Task) + '_report.json')

function Say([string]$Message) { Write-Host ('TICK_HARNESS ' + $Message) }

$running = @(Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'" |
    Where-Object { $_.CommandLine -like '*GrandTour.uproject*' })
if ($running.Count -gt 0) {
    Say ('refused: a GrandTour editor is running (pid ' + (($running | ForEach-Object { $_.ProcessId }) -join ',') + ')')
    exit 2
}
if (Test-Path $Boot) {
    Say "refused: $Boot already exists. It is not this run's; delete it by hand if it is a stale harness copy."
    exit 2
}

$bootText = @'
# Bootstrap written by Art/dressing/tick_harness.ps1 and deleted by it when its run ends (docs/LandscapeToolkit.md).
# Inert unless env GT_TOOLKIT_HARNESS names an existing task script. Found with no harness running? Delete it.
import os as _gt_os
_gt_task = _gt_os.environ.get("GT_TOOLKIT_HARNESS", "")
if _gt_task and _gt_os.path.isfile(_gt_task):
    import unreal as _gt_unreal
    _gt_unreal.log("GT_TOOLKIT_HARNESS bootstrap: running " + _gt_task)
    _gt_globals = {"__name__": "gt_toolkit_harness_task", "__file__": _gt_task}
    with open(_gt_task, encoding="utf-8") as _gt_file:
        exec(compile(_gt_file.read(), _gt_task, "exec"), _gt_globals)
'@

$createdPyDir = $false
$proc = $null
$outcome = 'not started'
$clock = [Diagnostics.Stopwatch]::StartNew()
try {
    if (-not (Test-Path $PyDir)) {
        New-Item -ItemType Directory -Path $PyDir | Out-Null
        $createdPyDir = $true
    }
    [IO.File]::WriteAllText($Boot, $bootText, (New-Object Text.UTF8Encoding $false))
    if (Test-Path $Report) { Remove-Item $Report -Force }

    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $Editor
    $psi.Arguments = '"' + $Uproject + '" ' + $Map + ' -NoSplash'
    $psi.UseShellExecute = $false
    $psi.EnvironmentVariables['GT_TOOLKIT_HARNESS'] = $Task
    $proc = [Diagnostics.Process]::Start($psi)
    Say ('started editor pid ' + $proc.Id + ': ' + $psi.Arguments)

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $finishedAt = $null
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $finishedAt -and (Test-Path $Report)) {
            try {
                if ((Get-Content $Report -Raw | ConvertFrom-Json).finished) {
                    $finishedAt = Get-Date
                    Say ('task finished at ' + [int]$clock.Elapsed.TotalSeconds + ' s; waiting for the editor to quit')
                }
            } catch { }
        }
        if ($finishedAt -and ((Get-Date) - $finishedAt).TotalSeconds -gt $QuitGraceSeconds) {
            $outcome = "killed: still running $QuitGraceSeconds s after the task finished"
            break
        }
        if ((Get-Date) -gt $deadline) {
            $outcome = "killed: $TimeoutMinutes min timeout"
            break
        }
    }
    if ($proc.HasExited) {
        $outcome = 'editor exited, code ' + $proc.ExitCode
    } else {
        Say $outcome
        & taskkill.exe /PID $proc.Id /T /F | Out-Null
        $proc.WaitForExit(60000) | Out-Null
    }
}
finally {
    if ($proc -and -not $proc.HasExited) {
        & taskkill.exe /PID $proc.Id /T /F | Out-Null
        $proc.WaitForExit(60000) | Out-Null
    }
    for ($i = 0; $i -lt 10 -and (Test-Path $Boot); $i++) {
        try { Remove-Item $Boot -Force } catch { Start-Sleep -Seconds 2 }
    }
    if ($createdPyDir -and (Test-Path $PyDir)) { Remove-Item $PyDir -Recurse -Force }
    $pyDirNote = if ($createdPyDir) { 'created and removed: ' + (-not (Test-Path $PyDir)) } else { 'existed before, kept' }
    Say ('bootstrap deleted: ' + (-not (Test-Path $Boot)) + '; Content/Python ' + $pyDirNote)
}
Say ('outcome: ' + $outcome + '; wall ' + [int]$clock.Elapsed.TotalSeconds + ' s')

if (-not (Test-Path $Report)) {
    Say "no report at $Report"
    exit 1
}
$r = Get-Content $Report -Raw | ConvertFrom-Json
foreach ($p in $r.steps.PSObject.Properties) {
    $v = if ($p.Value.ok) { ($p.Value.value | ConvertTo-Json -Compress -Depth 8) } else { $p.Value.error }
    if ($v.Length -gt 900) { $v = $v.Substring(0, 900) + '...' }
    Say ('step ' + $p.Name + ' ok=' + $p.Value.ok + ': ' + $v)
}
Say ('report ok=' + $r.ok + ' finished=' + $r.finished + ' timeline ' + ($r.timeline_s | ConvertTo-Json -Compress))
if ($r.ok -and $r.finished) { exit 0 } else { exit 1 }

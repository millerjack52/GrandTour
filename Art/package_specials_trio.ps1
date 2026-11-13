param(
    [ValidateSet('KadettA','E39Touring','SJ413')][string]$Car,
    [string]$Source = 'R6',
    [string]$Package = 'Package_v01'
)
$ErrorActionPreference = 'Stop'
if (-not $Car) { throw 'Specify -Car; each vehicle has its own source and package.' }
$projectRoot = Split-Path $PSScriptRoot -Parent
$blenderExe = 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
Push-Location $projectRoot
try {
    $steps = @(
        @{Name='audit'; Script='audit_specials_trio.py'; Extra=@('--source',$Source)},
        @{Name='package'; Script='package_specials_trio.py'; Extra=@('--source',$Source,'--package',$Package)},
        @{Name='validate'; Script='validate_specials_trio.py'; Extra=@('--package',$Package)},
        @{Name='review'; Script='review_specials_trio.py'; Extra=@('--package',$Package)}
    )
    foreach ($step in $steps) {
        $logPath = Join-Path $projectRoot "Saved/Logs/trio_${Car}_$($step.Name)_final.log"
        & $blenderExe -b --factory-startup --python-exit-code 1 --python "Art/Blender/$($step.Script)" -- --car $Car @($step.Extra) *> $logPath
        if ($LASTEXITCODE -ne 0) { throw "$Car $($step.Name) failed; see $logPath" }
        Write-Output "TRIO_STAGE_OK $Car $($step.Name)"
    }
} finally { Pop-Location }

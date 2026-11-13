# NP3 (docs/NATIVE_PLANT_KIT_PLAN.md): one Unreal at a time for the native plant kit.
#   powershell -NoProfile -ExecutionPolicy Bypass -File Art/native_plants.ps1 -Mode Import   # 20 bush/open + 15 S1 floor + 15 S2b verge + 11 S2a farm + 5 GP1 grass + 3 GP4a patch meshes -> /Game/GrandTour/Environment/NativePlants/v01
#       (a mesh already imported with its LOD count (3; 2 for grass), the manifest's hulls and size is skipped; -Reimport all|bush|open|floor|verge|farm|grass|patch forces a set again)
#   powershell -NoProfile -ExecutionPolicy Bypass -File Art/native_plants.ps1 -Mode Lineup   # /Game/GrandTour/ArtTests/NativePlants/L_NativePlants
#   powershell -NoProfile -ExecutionPolicy Bypass -File Art/native_plants.ps1 -Mode Check    # nine UE_<view>.png captures + asset readback
# Waits for Unreal to be free first (Art/wait_unreal_free.ps1), never kills anything it did not start, 20-minute timeout.
param([Parameter(Mandatory=$true)][ValidateSet('Import','Lineup','Check')][string]$Mode,[string]$Reimport='')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$out="$root\Art\Export\NativePlants\v01"
$spec=@{
    Import=@{script='import_native_plants.py';report='unreal-import-report.json'}
    Lineup=@{script='setup_native_plants_lineup.py';report='lineup-report.json'}
    Check=@{script='check_native_plants.py';report='capture-report.json'}
}[$Mode]
& "$PSScriptRoot\wait_unreal_free.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal is not free (editor, game or build still running); nothing started.'}
$log="$root\Saved\Logs\NativePlants-$Mode.log"
$env:GT_NP_REIMPORT=$Reimport   # read by import_native_plants.py (Import only)
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTLookKuwahara=0','-NoLoadStartupPackages',
    ('-ExecutePythonScript="'+$root+'\Art\Unreal\'+$spec.script+'"'),('-abslog="'+$log+'"'))
$started=(Get-Date).ToUniversalTime()
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
while(-not $p.WaitForExit(5000)){
    if(((Get-Date).ToUniversalTime()-$started).TotalMinutes -gt 20){Stop-Process -Id $p.Id;throw "Native plants $Mode exceeded twenty minutes; see $log"}
}
$p.WaitForExit()
$file="$out\$($spec.report)"
if(-not (Test-Path -LiteralPath $file)){throw "No $($spec.report) written; see $log"}
$item=Get-Item -LiteralPath $file
if($item.LastWriteTimeUtc -lt $started){throw "The editor did not write a fresh $($spec.report); see $log"}
$report=Get-Content -LiteralPath $file -Raw|ConvertFrom-Json
if(-not $report.ok){throw "Native plants $Mode failed: $($report.error)"}
if($Mode -eq 'Check'){
    $failed=@(Select-String -LiteralPath $log -Pattern 'Failed to compile Material (\S+)' | ForEach-Object {$_.Matches[0].Groups[1].Value} | Sort-Object -Unique)
    if($failed -match '/NativePlants/'){throw "A native plant material failed to compile; the captures need review ($log)"}
    # Pre-existing outside NP3 (docs/ROAD_BENCHMARK.md): M_GT_PostLook/M_GT_PostKuwahara fail their FDebugViewModePS permutation during high-res shots.
    if($failed.Count){Write-Output ("WARN other materials failed to compile (not NP3): " + ($failed -join ', '))}
}
Write-Output "NATIVE_PLANTS_$($Mode.ToUpper())_OK ($($spec.report), exit $($p.ExitCode))"

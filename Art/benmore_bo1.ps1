# Benmore optimisation BO1 (docs/BENMORE_OPTIMISATION_PLAN.md): Lumen scene membership on L_Benmore_GaeaReview.
# Runs Art/Unreal/apply_benmore_bo1.py in the full editor (off-screen), then parses the Lumen DumpStats blocks
# from Saved/Logs/BenmoreBO1.log into Art/Export/BenmoreGaea/BO1/bo1-report.json. No timings are collected.
#   powershell -NoProfile -File Art/benmore_bo1.ps1            apply: back up the map, set the flags, measure, save
#   powershell -NoProfile -File Art/benmore_bo1.ps1 -Measure   measure only (map already carries BO1), no save
# The caller runs `powershell -NoProfile -File Art/wait_unreal_free.ps1` first (own command); this script never
# kills or closes any process.
param([switch]$Measure)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$out=Join-Path $root 'Art/Export/BenmoreGaea/BO1'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$report=Join-Path $out 'bo1-report.json'
$script=$root+'/Art/Unreal/apply_benmore_bo1.py'
$env:GT_BO1_MODE=$(if($Measure){'measure'}else{'apply'})
$started=Get-Date
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 15"',('-ExecutePythonScript="'+$script+'"'),('-abslog="'+$root+'/Saved/Logs/BenmoreBO1.log"'))
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
if(-not $p.WaitForExit(40*60*1000)){throw "BO1 editor (pid $($p.Id)) still running after 40 minutes; not killed, check Saved/Logs/BenmoreBO1.log"}
if(-not (Test-Path -LiteralPath $report)){throw 'No BO1 report written'}
$file=Get-Item -LiteralPath $report
if($file.LastWriteTime -lt $started){throw 'No fresh BO1 report'}
& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' $script --parse-log
$parseExit=$LASTEXITCODE
$r=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
if(-not $r.ok){throw ('BO1 report ok=false: '+$r.error)}
if($parseExit -ne 0){throw 'BO1 log parse failed'}
Write-Output ('BENMORE_BO1_OK ('+$env:GT_BO1_MODE+'); report '+$report+'; structural/visual validation only, no timings')

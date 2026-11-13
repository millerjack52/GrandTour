$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
# Living mud LM5b (docs/MUD_VARIANTS.md): the four bog bake sets (Art/Export/MudStyleUE/T_MS_Bog*) into the four texture arrays
# TA_MS_Bog{Color,Normal,Rough,Height} and (MudRunner MRP) TA_MS_BogORH (slice = the variant; python Art/bake_mud_orh.py first).
# Repeatable: a re-run replaces the slices and rebuilds the arrays.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\import_mud_variants.py"'),('-abslog="'+$root+'\Saved\Logs\mud_variants_import.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\MudVariants\import-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No import report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
foreach($a in $report.arrays){Write-Output ("{0}: {1} slices of {2} x {3}, sRGB {4}, {5}; created {6}; Python's own Source Textures gave {7} slices{8}; rebuilt: {9}" -f $a.asset,$a.source_slices,$a.size[0],$a.size[1],$a.srgb,$a.compression,$a.created,$a.python_route.slices,$(if($a.python_route.error){" (error: $($a.python_route.error))"}else{''}),$a.rebuilt)}
Write-Output $report.route
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
Write-Output 'MUD_VARIANTS_IMPORT_OK'

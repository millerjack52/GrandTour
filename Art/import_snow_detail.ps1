$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
# LM4b item 4 (docs/LIVING_MUD_PLAN.md LM4b): the snow-clump detail height map from Art/tools/bake_snow_detail.py into /Game/GrandTour/Textures/Snow.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\import_snow_detail.py"'),('-abslog="'+$root+'\Saved\Logs\snow_detail_import.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\LiveSnowDrive\detail-import-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No import report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output ("{0} <- {1} ({2:N2} MB, source {3}): {4} x {5}, sRGB {6}, {7}, address {8}" -f $report.asset,$report.source,($report.source_bytes/1048576.0),$report.source_format,$report.size[0],$report.size[1],$report.srgb,$report.compression,($report.address -join '/'))
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
Write-Output 'SNOW_DETAIL_IMPORT_OK'

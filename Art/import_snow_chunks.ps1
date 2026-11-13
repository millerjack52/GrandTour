$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
# LM4 item 4 (docs/LIVING_MUD_PLAN.md LM4): the snow shards from Art/Blender/build_snow_chunks.py into /Game/GrandTour/Mud/SnowChunks.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\import_snow_chunks.py"'),('-abslog="'+$root+'\Saved\Logs\snow_chunks_import.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\SnowChunks\import-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No import report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
foreach($m in $report.meshes){Write-Output ("{0}: {1} triangles (source {2}), {3} cm (across {4}, thickness {5}), simple collision {6}, material {7}" -f $m.asset,$m.triangles,$m.source_triangles,($m.size_cm -join ' x '),$m.across_cm,$m.thickness_cm,$m.simple_collision,$m.material)}
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
Write-Output 'SNOW_CHUNKS_IMPORT_OK'

param([switch]$AllowGame)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5): the mud chunks (six, each with its UCX_ hull) from Art/Blender/build_mud_chunks.py
# into /Game/GrandTour/Mud/Chunks, as Art/import_mud_clods.ps1 does the clods. -AllowGame runs it with a game open; an editor refuses.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'An editor is running'}
if(-not $AllowGame -and (Get-Process GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue)){throw 'A game is running (-AllowGame runs anyway)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\import_mud_chunks.py"'),('-abslog="'+$root+'\Saved\Logs\mud_chunks_import.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\MudChunks\import-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No import report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
foreach($m in $report.meshes){Write-Output ("{0} ({1}): {2} triangles (source {3}), {4} cm, bottom {5} cm (embed {6}), volume {7} cm3, hull {8} cm3 ({9} vertices), convex {10}, simple collision {11}, data {12}, material {13}" -f $m.asset,$m.family,$m.triangles,$m.source_triangles,($m.size_cm -join ' x '),$m.bottom_cm,$m.embed_cm,$m.volume_cm3,$m.hull_volume_cm3,$m.hull_vertices,$m.convex,$m.simple_collision,$m.chunk_data,$m.material)}
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
Write-Output 'MUD_CHUNKS_IMPORT_OK'

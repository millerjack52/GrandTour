$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
# LM2b/LM2c (docs/LIVING_MUD_PLAN.md): the clods (LM2c: ten) from Art/Blender/build_mud_clods.py into /Game/GrandTour/Mud/Clods.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\import_mud_clods.py"'),('-abslog="'+$root+'\Saved\Logs\mud_clods_import.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\MudClods\import-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No import report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
foreach($m in $report.meshes){Write-Output ("{0} ({6}): {1} triangles (source {2}), {3} cm, simple collision {4}, material {5}" -f $m.asset,$m.triangles,$m.source_triangles,($m.size_cm -join ' x '),$m.simple_collision,$m.material,$m.family)}
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
Write-Output 'MUD_CLODS_IMPORT_OK'

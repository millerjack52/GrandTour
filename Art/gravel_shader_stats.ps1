$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is running'}
# Deformable gravel DG1 (docs/DEFORMABLE_GRAVEL_PLAN.md item 6): static shader stats of M_GT_Gravel vs the study's M_GravelField.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\gravel_shader_stats.py"'),('-abslog="'+$root+'\Saved\Logs\gravel_shader_stats.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\DeformableGravel\shader-stats.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No stats written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
foreach($r in $report.rows){Write-Output ("{0} ({1}): pixel {2}, vertex {3}, samplers {4}, pixel texture samples {5}" -f $r.role,$r.material,$r.pixel_instructions,$r.vertex_instructions,$r.samplers,$r.pixel_texture_samples)}
Write-Output 'GRAVEL_SHADER_STATS_OK'

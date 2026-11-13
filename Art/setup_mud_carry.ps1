$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
# MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1): the splat atlas import, MF_MudCover, M_GT_MudSplatDecal, the ground and grass
# wiring (Art/Unreal/mud_cover.py). Bake first: Art/Blender/build_mud_splats.py. Then & Art/setup_live_mud_drive.ps1 and
# & Art/setup_mud_variants.ps1 rebuild the strips with it.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_mud_carry.py"'),('-abslog="'+$root+'\Saved\Logs\mud_carry_setup.log"'))
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\MudSplats\setup-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No setup report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
foreach($t in $report.textures){Write-Output ("texture {0}: {1}, {2} x {3}" -f $t.asset,$t.compression,$t.size[0],$t.size[1])}
Write-Output ("collection: added [{0}], {1} scalars" -f ($report.collection.added -join ', '),$report.collection.scalars)
Write-Output ("function {0}: created {1}, {2} expressions" -f $report.function.function,$report.function.created,$report.function.expressions)
Write-Output ("decal {0}: {1}, {2}" -f $report.decal.material,$report.decal.domain,$report.decal.blend)
foreach($g in $report.ground){if($g.skipped){Write-Output "ground $($g.material): skipped ($($g.skipped))"}else{Write-Output ("ground {0}: weather {1}, tangent {2}; BaseColor {3}, Roughness {4}, Normal {5}" -f $g.material,$g.weather,$g.tangent,$g.BaseColor,$g.Roughness,$g.Normal)}}
foreach($g in $report.grass){if($g.skipped){Write-Output "grass $($g.material): skipped ($($g.skipped))"}else{Write-Output ("grass {0}: created {1}, base {2}, weather {3}, dry colour {4}" -f $g.material,$g.created,$g.base,$g.weather,($g.dry_colour -join ' '))}}
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
Write-Output 'MUD_CARRY_SETUP_OK'

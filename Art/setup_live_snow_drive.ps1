$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Living mud LM3a + LM3b + LM3c (docs/LIVE_SNOW_DRIVE.md): rebuilds L_SnowDrive and the snow materials (M_GT_Snow, M_GT_Clod_Snow) and the landscape's snow apron.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running (GoWR, GoW and FarCry6 are checked)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_live_snow_drive.py"'),('-abslog="'+$root+'\Saved\Logs\live_snow_setup.log"'))
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\LiveSnowDrive\setup-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No setup report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
if($p.ExitCode -ne 0){Write-Output "Editor exit $($p.ExitCode) after a fresh ok report (not judged)"}
foreach($m in $report.materials){Write-Output ("material {0}: compile errors {1}" -f $m.material,$m.compile_errors.Count)}
# LM3b: the subsurface route, the landscape apron, the instruction counts, and any shader compile error the log names.
$sss=$report.materials[0].subsurface
Write-Output ("M_GT_Snow subsurface: {0}{1}" -f $sss.route,$(if($sss.slab_error){" ($($sss.slab_error))"}else{''}))
# LM3c item 4: the snow clod's route (M_GT_Snow's Slab, or the legacy Default Lit fallback) and its colour.
$csss=$report.materials[1].subsurface
if($csss){Write-Output ("M_GT_Clod_Snow: colour {0}, subsurface {1}{2}" -f ($report.materials[1].color -join ', '),$csss.route,$(if($csss.slab_error){" ($($csss.slab_error))"}else{''}))}
if($report.apron){Write-Output ("landscape apron: box {0} - {1} cm, {2} cm out, layer {3}; wrappers {4}" -f ($report.apron.box_min -join ','),($report.apron.box_max -join ','),$report.apron.apron_cm,$report.apron.snow_layer,(($report.apron.wrappers|ForEach-Object{$_.wrapper})-join ', '))}
foreach($st in $report.material_stats){Write-Output ("stats {0}: pixel instructions {1}, vertex {2}, samplers {3}, pixel texture samples {4}" -f $st.material,$st.pixel_instructions,$st.vertex_instructions,$st.samplers,$st.pixel_texture_samples)}
if($report.material_stats_error){Write-Output "stats error: $($report.material_stats_error)"}
# LM3c item 5: Substrate's compile output per material (material type and lighting tile, BSDF features, pass-through).
foreach($line in $report.substrate_info){Write-Output ("substrate " + $line.Substring(0,[math]::Min(700,$line.Length)))}
if($report.substrate_info_error){Write-Output "substrate info error: $($report.substrate_info_error)"}
$logLines=Get-Content "$root\Saved\Logs\live_snow_setup.log" -ErrorAction SilentlyContinue
# The edits compile half-wired graphs on the way, so the snow materials are read after the line the script logs once they
# are built, and the landscape after the one it logs once its apron is wired.
$mark=$logLines.Count;$markLand=$logLines.Count
for($i=0;$i -lt $logLines.Count;$i++){if($logLines[$i] -match 'LM3B_SNOW_MATERIALS_BUILT'){$mark=$i};if($logLines[$i] -match 'LM3B_SNOW_LANDSCAPE_BUILT'){$markLand=$i}}
$bad=@();for($i=$mark;$i -lt $logLines.Count;$i++){$l=$logLines[$i];$hit=($l -match '(M_GT_Snow\.|M_GT_Clod_Snow).*(rror|ailed)|(rror|ailed).*(M_GT_Snow\.|M_GT_Clod_Snow)') -or ($i -ge $markLand -and $l -match 'M_SnowLandscape.*(rror|ailed)|(rror|ailed).*M_SnowLandscape');if($hit){$bad+=[pscustomobject]@{Line=($l+' | '+$(if($i+1 -lt $logLines.Count){$logLines[$i+1]}else{''}))}}}
$bad=$bad|Select-Object -First 12
if($bad){foreach($b in $bad){Write-Output ("log: " + $b.Line.Substring(0,[math]::Min(400,$b.Line.Length)))};throw 'shader or material errors in the setup log (above)'}
Write-Output ("snow {0}-{1} m, drift {2}-{3} m at {4} cm ({5}); landscape {6}, Snow row albedo {7} rough {8}" -f $report.snow_m[0],$report.snow_m[1],$report.drift.start_m,$report.drift.end_m,$report.drift.depth_cm,$report.drift.how,$report.landscape_material,$report.snow_row.albedo,$report.snow_row.rough)
Write-Output 'LIVE_SNOW_SETUP_OK'

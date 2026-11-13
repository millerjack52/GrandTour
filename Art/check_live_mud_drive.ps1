param([switch]$AllowGame,[switch]$Profile)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md): by default a fixed 1/60 s step, the scene rendered only for the pictures,
# no CSV profile (GT_CHECK_NO_PROFILE=1), so -AllowGame runs it with a game open. -Profile is the owner's cost run as before: the real
# time step, every frame rendered (GT_CHECK_RENDER_ALWAYS=1), -csvGpuStats and the profiled phases.
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An editor is running'}
if(-not $AllowGame -and (Get-Process GrandTour,FarCry6,GoW,GoWR -ErrorAction SilentlyContinue)){throw 'A game is running (-AllowGame runs anyway)'}
$env:GT_CHECK_NO_PROFILE=$(if($Profile){'0'}else{'1'});$env:GT_CHECK_RENDER_ALWAYS=$(if($Profile){'1'}else{'0'})
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad',$(if($Profile){'-csvGpuStats'}else{'-UseFixedTimeStep'}),$(if($Profile){'-NoFixedStep'}else{'-FPS=60'}),'-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-ExecutePythonScript="'+$root+'\Art\Unreal\check_live_mud_drive.py"'),('-abslog="'+$root+'\Saved\Logs\live_mud_drive.log"'))
# LM2b phase B (2026-10-05): with a game in the foreground the hidden editor throttled to under 1 frame a second and the car
# never moved; the editor's background throttle is off for this run (the run's own settings, nothing saved).
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$code=$p.ExitCode
# LM1 housekeeping (docs/LIVING_MUD_PLAN.md LM1, item 4): the check is judged by its report, written after this run
# started and saying ok: true. The editor's exit code is printed, not judged: since 2026-09-29 the editor exits
# -1073741819 (0xC0000005) after "Log file closed", with no crash dump and no Windows fault event (LM0).
$file=Get-Item "$root\Art\Export\LiveMudDrive\drive-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No drive report written by this run (editor exit $code)"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw "Drive check failed (editor exit $code): $($report.error)"}
if($code -eq -1073741819){Write-Output 'Editor exit -1073741819 (0xC0000005) after the report: the known shutdown fault (LM0), not a check failure'}
elseif($code -ne 0){Write-Output "Editor exit $code after a fresh ok report (not judged)"}
Write-Output ("viewport: $($report.viewport_size -join 'x') (play: $($report.play_mode); first window $($report.viewport_retry -join 'x'), retried: $($report.play_mode_retry))")
foreach($r in $report.runs){Write-Output ("{0}: end {1:N2} m in {2:N1} s, max lateral {3:N2} m, added {4:N0} cm^3, max sink {5:N2} m, water {6:N2} m; settle frames {7} mean {8} ms max {9} ms awake peak {10}; upload mean {11} ms max {12} ms" -f $r.run,$r.end_x_m,$r.elapsed_s,$r.max_lateral_m,$r.volume_added_cm3,$r.max_sink_m,$r.max_water_m,$r.settle_frames,$r.settle_mean_ms,$r.settle_max_ms,$r.settle_awake_peak,$r.upload_mean_ms,$r.upload_max_ms)}
# LM2a housekeeping 2: per feature mean <= 0.3 ms and p99 <= 0.7 ms, the max reported (LM2b's clods: game-thread mean <= 0.1 ms too).
foreach($r in $report.runs){
  if($r.settle_gate){$g=$r.settle_gate;Write-Output ("{0}: settle mean {1} / p99 {2} / max {3} ms (gate mean <= 0.3, p99 <= 0.7: {4}); upload p99 {5} ms" -f $r.run,$g.mean_ms,$g.p99_ms,$g.max_ms,$(if($g.ok){'PASS'}else{'FAIL'}),$r.upload_p99_ms)}
  if($r.clod_gate){$g=$r.clod_gate;Write-Output ("{0}: clods {1} frames, mean {2} / p99 {3} / max {4} ms (gate: {5}; game-thread mean <= 0.1: {6})" -f $r.run,$r.clod_frames,$g.mean_ms,$g.p99_ms,$g.max_ms,$(if($g.ok){'PASS'}else{'FAIL'}),$(if($g.ok_gt_mean){'PASS'}else{'FAIL'}))}
  if($r.clods){$c=$r.clods.total;Write-Output ("{0}: clods live {1}; from bank {2}, throw {3}; squashed {4}, sunk {5}, recycled {6}; dropped {7}" -f $r.run,$c.live,$c.bank,$c.throw,$c.squashed,$c.sunk,$c.recycled,$c.dropped)}
  if($r.throw){$t=$r.throw;Write-Output ("{0}: throw - wheels {1} cm^3, spray emitted {2} / landed {3} / lost {4} (lost share {5}) / pending {6}; patches returned {7}, deposited {8}; lumps flattened {9}" -f $r.run,($t.wheels_thrown_cm3 -join ' / '),$t.spray_emitted_cm3,$t.spray_landed_cm3,$t.spray_lost_cm3,$t.lost_share,$t.spray_pending_cm3,$t.patches_returned_cm3,$t.patches_deposited_cm3,$t.lumps_flattened_cm3)}
}
foreach($f in $report.profiles){Write-Output ("profile {0}: {1} frames, frame {2} / game {3} / GPU {4} ms mean (median {5} / {6} / {7}); GTMud/GameThread/Settle {8} ms mean; {9}" -f $f.run,$f.frames,$f.FrameTime.mean,$f.GameThreadTime.mean,$f.GPUTime.mean,$f.FrameTime.median,$f.GameThreadTime.median,$f.GPUTime.median,$f.'GTMud/GameThread/Settle'.mean,$f.csv)}
if($report.settle_pair){$s=$report.settle_pair;Write-Output ("settle pair (Settle 1) at x {0} cm, rut y {1:N1} cm: core {2} cm at 0.3 s -> {3} cm at 5 s, crest {4} -> {5} cm, fresh at the core {6} -> {7}, D {8} -> {9} over {10} cells" -f $s.spot_x,$s.rut_y,$s.'core_cm_0.3',$s.core_cm_5,$s.'crest_cm_0.3',$s.crest_cm_5,$s.'fresh_core_0.3',$s.fresh_core_5,$s.'detail_d_0.3',$s.detail_d_5,$s.detail_cells)}
# LM1b: the same pair with gt.Mud.Settle 0, from the same camera (Mud_Settle_0s_Off.png / Mud_Settle_5s_Off.png).
if($report.settle_pair_off){$s=$report.settle_pair_off;Write-Output ("settle pair (Settle 0) at x {0} cm, rut y {1:N1} cm (its own {2:N1}): core {3} cm at 0.3 s -> {4} cm at 5 s, crest {5} -> {6} cm, D {7} -> {8} over {9} cells" -f $s.spot_x,$s.rut_y,$s.own_rut_y,$s.'core_cm_0.3_off',$s.core_cm_5_off,$s.'crest_cm_0.3_off',$s.crest_cm_5_off,$s.'detail_d_0.3_off',$s.detail_d_5_off,$s.detail_cells)}
# LM2a housekeeping 4: the standstill crawl (rows in crawl.csv).
foreach($k in 'crawl','crawl_off'){if($report.$k){$c=$report.$k;Write-Output ("{0}: {1} samples from x {2} m, 2.3 m covered at {3} s; max RutClimb {4}, max hold drag {5} N, max |hold push| {6} N, max (30 cm ahead - under) {7} cm" -f $k,$c.samples,$c.start_x_m,$c.seconds_to_2_3_m,$c.max_rut_climb,$c.max_hold_drag_n,$c.max_abs_hold_lateral_n,$c.max_ahead_minus_under_cm)}}
# LM2a's spin test and LM2b's clods.
if($report.spin){$s=$report.spin;Write-Output ("spin test at x {0} cm, y {1} cm (Bog {2}): x {3} -> {4} m in 3 s" -f $s.x,$s.y,$s.bog,$s.start_x_m,$s.end_x_m)
  foreach($w in $s.wheels){Write-Output ("  wheel {0}: hole {1} cm, mound {2} cm at {3} m behind (lumps there {4} cm), sinkage {5} m, thrown {6} cm^3" -f $w.wheel,$w.hole_cm,$w.mound_cm,$w.mound_behind_m,$w.mound_lump_cm,$w.sinkage_m,$w.thrown_cm3)}
  $t=$s.after.throw;Write-Output ("  throw: spray emitted {0} / landed {1} / lost {2} cm^3 (lost share {3}), blobs {4} / {5} / {6}" -f $t.spray_emitted_cm3,$t.spray_landed_cm3,$t.spray_lost_cm3,$t.lost_share,$t.blobs.emitted,$t.blobs.landed,$t.blobs.lost)
  $c=$s.after.clods.total;Write-Output ("  clods after the spin: live {0}; bank {1}, throw {2}; squashed {3}, sunk {4}, recycled {5}" -f $c.live,$c.bank,$c.throw,$c.squashed,$c.sunk,$c.recycled)}
if($report.clod_cap){$c=$report.clod_cap;Write-Output ("clods at the cap: {0} added, live {1}" -f $c.added,$c.clods.total.live);if($c.on_game_thread){Write-Output ("  game thread mean {0} / p99 {1} / max {2} ms" -f $c.on_game_thread.mean_ms,$c.on_game_thread.p99_ms,$c.on_game_thread.max_ms)}
  foreach($f in $report.profiles | Where-Object { $_.run -like 'clods_cap_*' }){$extra=($f.PSObject.Properties | Where-Object { $_.Name -match 'basepass|shadowdepth' } | ForEach-Object { "$($_.Name) $($_.Value.mean)" }) -join ', ';Write-Output ("  {0}: GPU {1} ms mean (p99 {2}); {3}" -f $f.run,$f.GPUTime.mean,$f.GPUTime.p99,$extra)}}
if($report.dark_line){foreach($l in $report.dark_line.lines){$a=$l.points[0];$b=$l.points[-1];Write-Output ("dark-line candidate: patch {0} {1} side {2}: {3} points in the shot, ({4},{5}) .. ({6},{7})" -f $l.patch,$l.line,$l.side,$l.points.Count,$a[0],$a[1],$b[0],$b[1])}}
if($report.dark_line_error){Write-Output "dark-line projection failed: $($report.dark_line_error)"}
Write-Output 'LIVE_MUD_DRIVE_OK'

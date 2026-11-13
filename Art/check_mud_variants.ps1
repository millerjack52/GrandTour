param([switch]$AllowGame,[int]$PoolSize=0,[int]$Fps=60)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Living mud LM5b (docs/MUD_VARIANTS.md): one dry crossing of L_MudVariants at full throttle in low range with the diff lock
# (Firm, Standard, Deep, Stony), per section its mean speed and sinkage, then per section an on-foot picture and a close-up.
# No cost or timing measurement (the owner tests performance).
# MR2 (2026-10-08, the owner's rule): -AllowGame runs it with a game open (GoWR, GoW, FarCry6); an editor still refuses.
# MRP follow-up 3: -PoolSize <MB> sets r.Streaming.PoolSize for the run (runs on the 6 GB card ended out of video memory).
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'An editor is running'}
if(-not $AllowGame -and (Get-Process FarCry6,GoW,GoWR -ErrorAction SilentlyContinue)){throw 'A game is running (GoWR, GoW and FarCry6 are checked; -AllowGame runs anyway)'}
# As the mud and snow checks: the editor's background throttle is off for this run (the run's own settings, nothing saved).
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md): a fixed 1/60 s step; the script renders only for its pictures.
# -Fps <n> (GR1c checks follow-up, the frame-rate finding): another fixed step for a comparison run (60 is the check's own).
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-UseFixedTimeStep',"-FPS=$Fps",'-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900',('-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100'+$(if($PoolSize -gt 0){",r.Streaming.PoolSize $PoolSize"}else{''})+'"'),('-ExecutePythonScript="'+$root+'\Art\Unreal\check_mud_variants.py"'),('-abslog="'+$root+'\Saved\Logs\mud_variants_drive.log"'))
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
# Judged by a fresh ok report, as the mud check; the editor's -1073741819 exit is the known shutdown fault (LM0).
$file=Get-Item "$root\Art\Export\MudVariants\drive-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No drive report written by this run (editor exit $code)"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if($code -eq -1073741819){Write-Output 'Editor exit -1073741819 (0xC0000005) after the report: the known shutdown fault (LM0), not a check failure'}
elseif($code -ne 0){Write-Output "Editor exit $code after a fresh report (not judged)"}
Write-Output ("viewport: $($report.viewport_size -join 'x') (play: $($report.play_mode)); weather $($report.weather); box gaps $($report.box_gaps_cm -join ' / ') cm")
foreach($q in $report.patches){Write-Output ("patch {0} (section {1}, slot {2}): {3}, profile {4}, sinkage x{5}/x{6}, friction x{7}, RecoverShare {8}, LumpShare {9}, ThrowMax {10}, water table {11} cm; mesh MudVariant {12} ({13}), clod instance {14} ({15})" -f $q.variant,$q.section,$q.slot,$q.mud_variant,$q.has_profile,$q.max_sinkage_scale,$q.sinkage_rate_scale,$q.friction_scale,$q.recover_share,$q.lump_share,$q.throw_max,$q.water_table_cm,$q.mesh_mud_variant,$(if($q.mesh_slice_ok){'ok'}else{'WRONG'}),$q.clod_mud_variant,$(if($q.clod_slice_ok){'ok'}else{'WRONG'}))}
if($report.drive){$d=$report.drive;Write-Output ("drive: {0}, completed {1}, end {2} m in {3} s, max lateral {4} m, longest stop {5} s at {6} m, lowered {7} cm^3" -f $d.ended,$d.completed,$d.end_x_m,$d.elapsed_s,$d.max_lateral_m,$d.longest_stop_s,$d.longest_stop_at_m,$d.lowered_cm3)}
foreach($t in $report.teleport_pass){Write-Output ("MR2 scripted pass: {0} from {1} m to {2} m in {3} s (real), 6 m into it {4}" -f $t.section,$t.from_m,$t.end_m,$t.s,$t.into)}
foreach($s in $report.sections){Write-Output ("{0} {1}-{2} m: {3} s, mean {4} m/s ({5} km/h), min {6} m/s; sinkage max {7} cm, mean {8} cm over {9} wheel samples; lowered {10} cm^3 while inside; mean friction scale in the mud {11}" -f $s.variant,$s.start_m,$s.end_m,$s.time_s,$s.mean_speed_mps,$s.mean_speed_kmh,$s.min_speed_mps,$s.max_sinkage_cm,$s.mean_sinkage_cm,$s.wheel_samples,$s.lowered_cm3_while_inside,$s.mean_friction_scale)}
foreach($i in $report.images){Write-Output "picture: $i"}
# MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 item 8): the carried mud, the muddy grass, the splats (functional, no timing).
if($report.mr1){
  $m=$report.mr1
  Write-Output ("MR1 stop at {0} m, wheel mud loads {1}" -f $m.stop_x_m,($m.loads_at_stop -join ' '))
  if($m.exit){Write-Output ("MR1 exit: reached {0} ({1} m in {2} s), loads {3}" -f $m.exit.reached,$m.exit.x_m,$m.exit.s,($m.exit.loads -join ' '));foreach($l in $m.exit.profile){Write-Output ("MR1 exit G, {0} side, 197-221 m: per 5 m {1}; gaps {2} of {3} cells; max {4}; CPU G / GPU G / GPU B at each 5 m's best cell: {5}" -f $l.side,($l.mean_by_5m -join ' / '),$l.gap_share,$l.cells,$l.max_g,(($l.cpu_gpu_g_b|ForEach-Object{$_ -join ' '}) -join '; '))}}
  if($m.grass){$g=$m.grass;Write-Output ("MR1 grass: reached {0} (end {1} m) in {2} s; verge points {3}, with mud {4}, mean G {5}; load on the verge {6} -> {7}; loads {8}" -f $g.reached,($g.end_m -join ', '),$g.s,$g.verge_points,$g.verge_with_mud,("{0} (GPU {1})" -f $g.verge_mean_g,$g.verge_mean_gpu_g),$g.verge_load_first,$g.verge_load_last,($g.loads -join ' '))}
  if($m.spin){$b=$m.spin.before;$a=$m.spin.after;Write-Output ("MR1 spin-up (6 s): thrown {0} blobs, landed {1}, lost {2}, splatted {3} ({4} cm^3); landscape splats {5}, decals {6} (live {7}), traces {8}, capped {9}, ignored hits {10}; decals on: {11}; end {12} m, loads {13}" -f ($a.thrown_blobs-$b.thrown_blobs),($a.landed_blobs-$b.landed_blobs),($a.lost_blobs-$b.lost_blobs),($a.splatted_blobs-$b.splatted_blobs),($a.splatted_cm3-$b.splatted_cm3),($a.landscape_splats-$b.landscape_splats),($a.decal_splats-$b.decal_splats),$a.live_decals,($a.traces-$b.traces),($a.capped_traces-$b.capped_traces),($a.ignored_hits-$b.ignored_hits),($m.spin.decals_on -join ', '),$m.spin.end_x_m,($m.spin.loads -join ' '))}
  if($m.spin.synthetic){$sy=$m.spin.synthetic;Write-Output ("MR1 spin-up: no blob of its own reached a mesh; synthetic blob paths at the post {0}, splats {1}; decals on: {2}" -f $sy.paths,$sy.splats,($sy.decals_on -join ', '))}
  if($m.counts_after){$c=$m.counts_after;Write-Output ("MR1 whole run: carried blots {0} (gap places {1}), landscape splats {2} (by the height test {3}), decals {4} (held for shaders {5}, waiting {6}), traces {7}, capped {8}, skipped by the band {9}; body traces {10}, capped {11}, blobs on the car {12} ({13} cm^3)" -f $c.carried_blots,$c.carried_gaps,$c.landscape_splats,$c.height_splats,$c.decal_splats,$c.held_decals,$c.pending_decals,$c.traces,$c.capped_traces,$c.skipped_traces,$c.body_traces,$c.body_capped,$c.blobs_on_car,$c.on_car_cm3)}
  foreach($k in @(@('drive',$report.drive.splats_per_second),@('spin-up',$m.spin.per_second),@('whole run',$m.whole_run_per_second))){$p=$k[1];if($p){Write-Output ("MR2 traces per second, {0} ({1} s of play): {2} traced, {3} refused, {4} skipped by the band; {5} height splats; body {6} traced, {7} refused, {8} blobs on the car; {9} frames in {10} s real ({11} a second), {12} traced and {13} refused a frame" -f $k[0],$p.play_s,$p.traces_per_s,$p.refused_per_s,$p.skipped_per_s,$p.height_splats,$p.body_traces_per_s,$p.body_refused_per_s,$p.blobs_on_car,$p.frames,$p.real_s,$p.fps,$p.traces_per_frame,$p.refused_per_frame)}}
  if($m.spin){Write-Output ("MR2 decal material ready at the spin-up: {0}" -f $m.spin.decal_material_ready)}
  if($m.grass.camera_g_wet){Write-Output ("MR2 grass camera at the verge point {0}: G {1}, B {2}" -f ($m.grass.camera_at_m -join ', '),$m.grass.camera_g_wet[0],$m.grass.camera_g_wet[1])}
}
if($report.mr2){$b=$report.mr2.state;Write-Output ("MR2 car at {0} m: {1}" -f ($report.mr2.car_at_m -join ', '),$b.describe);Write-Output ("MR2 mud line {0} cm, coat line {1} cm, wash {2} cm at {3}, MudWet {4}, tyres {5}, hits {6} (glass {7}); wheel bottoms Z {8}, wheel geometry {9}, tyre slots {10}" -f $b.mud_line_cm,$b.coat_line_cm,$b.wash_cm,$b.wash_amount,$b.mud_wet,($b.tyres -join ' / '),$b.hits,$b.glass_hits,$b.mud_base_z,($b.wheel_geom -join ' / '),$b.tyre_slots)
  # MR2b: the spray fans, and the droplet-density row from Car_Muddy_Side (system Python: numpy and Pillow).
  Write-Output ("MR2b fans FanCoat {0}, FanDir {1} (FL / FR / RL / RR; +1 behind the arch)" -f ($b.fan_coat -join ' / '),($b.fan_dir -join ' / '))
  foreach($t in $report.fan_trace){Write-Output ("MR2b fan sides at {0} ({1} m): FanDir {2}, FanSide {3}, FanCoat {4}" -f $t.at,$t.x_m,($t.fan_dir -join ' / '),($t.fan_side -join ' / '),($t.fan_coat -join ' / '))}
  if($report.mr1.grass.parked_at_m){Write-Output ("MR2b grass camera: the car parked at {0} m; verge points crossed and not parked on {1}" -f ($report.mr1.grass.parked_at_m -join ', '),$report.mr1.grass.verge_points_crossed)}
  if($report.mr2.droplet_boxes){try{& python "$root\Art\count_car_droplets.py" "$root\Art\Export\MudVariants\drive-report.json" "$root\Art\Export\MudVariants\Car_Muddy_Side.png"}catch{Write-Output "MR2b droplet count did not run: $_"}}}
# MudRunner MR3 (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1): the churned rut pool in Deep and the same camera 60 s later.
if($report.mr3){$r=$report.mr3
  if($r.churn){Write-Output ("MR3 churn: {0} s of game time ({1} s real) from {2} m to {3} m; wheel slip {4}; sinkage {5} cm" -f $r.churn.game_s,$r.churn.real_s,$r.churn.from_m,($r.churn.end_m -join ', '),($r.churn.slip -join ' / '),($r.churn.sink_cm -join ' / '))}
  if($r.spot){Write-Output ("MR3 spot {0}, {1} m: box turbidity {2}, cell {3}, mud {4} cm under a {5} cm table" -f $r.spot.x_m,$r.spot.y_m,$r.spot.box_turbidity,$r.spot.cell,$r.spot.mud_cm,$r.spot.water_table_cm)}
  Write-Output ("MR3 before the churn: {0}" -f $r.before_churn)
  Write-Output ("MR3 at Rut_Muddy: {0}" -f $r.at_muddy)
  if($r.at_muddy_low){Write-Output ("MR3b at Rut_Muddy_Low ({0} s of game time after Rut_Muddy): {1}" -f $r.muddy_low_after_game_s,$r.at_muddy_low)}
  if($r.settled_after){Write-Output ("MR3 at Rut_Settled ({0} s of game time later, {1} s real): {2}; the spot's cell {3}" -f $r.settled_after.game_s,$r.settled_after.real_s,$r.at_settled,$r.cell_settled)}
  if($r.at_settled_low){Write-Output ("MR3b at Rut_Settled_Low: {0}" -f $r.at_settled_low)}}
# MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP item 4): the PBR and POM pictures, and the PBR validation rows from the buffer dumps.
if($report.mrp){$m=$report.mrp
  foreach($q in $m.pictures){Write-Output ("MRP picture {0}: gt.Mud.POM {1}, gt.Mud.PBR {2}, gt.Mud.POMShadow {3}" -f $q.name,$q.pom,$q.pbr,$q.shadow)}
  if($m.car){Write-Output ("MRP car at {0} m: MudWet {1}, mud line {2} cm, coat line {3} cm, tyres {4}" -f ($m.car_at_m -join ', '),$m.car.mud_wet,$m.car.mud_line_cm,$m.car.coat_line_cm,($m.car.tyres -join ' / '))}
  if($m.at_rut_settled_pbr){Write-Output ("MRP rut water at Rut_Settled_PBR: {0}" -f $m.at_rut_settled_pbr)}
  try{& python "$root\Art\sample_mud_pbr.py" "$root\Art\Export\MudVariants\drive-report.json"}catch{Write-Output "MRP sampler did not run: $_"}}
# MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4 item 6): the soft spots' CPU maps, the pictures, the speeds and the wheel path's soft share.
if($report.soft){$m=$report.soft
  foreach($q in $m.patches){Write-Output ("MR4 {0}: soft spots {1}, amplitude {2}, gt.Mud.SoftSpots {3}, soft share {4}, blobs {5}, lerp means sink {6} friction {7}; wheel path (line +-1 m) soft share {8} in the section, {9} in the box; map {10}" -f $q.variant,$q.has_soft_spots,$q.amplitude,$q.switch,$q.share,$q.blobs,$q.mean_sink_lerp,$q.mean_friction_lerp,$q.wheel_path_share_section,$q.wheel_path_share_box,$q.map)}
  foreach($k in @('Standard','Firm')){$b=$m.blobs.$k;if($b){Write-Output ("MR4 {0} view's blob: {1} m2 at {2}, {3} cm" -f $k,$b.area_m2,$b.x_cm,$b.y_cm)}}
  foreach($q in $m.sections){Write-Output ("MR4 {0}: mean speed {1} m/s against the committed {2} m/s (x{3}); mean sinkage {4} cm against {5} cm; wheel path soft share {6}" -f $q.variant,$q.mean_speed_mps,$q.committed_mean_speed_mps,$q.speed_ratio,$q.mean_sinkage_cm,$q.committed_mean_sinkage_cm,$q.wheel_path_soft_share)}
  Write-Output ("MR4 baseline from {0}" -f $m.baseline_from)}
# MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 item 7): the chunks per section before driving, after the drive and at the end.
if($report.chunks){$m=$report.chunks
  foreach($tag in @('before','after_drive','end')){$t=$m.$tag;if($t){
    foreach($q in $t.sections){Write-Output ("MR5 {0} {1}: {2} live (target {3}, planned {4}, spawned {5}, no ground {6}; {7} m2 x{8}), breaks wheel {9} / impulse {10} / landing {11}, lost {12}, deposited {13} cm3, lost {14} cm3, awake peak {15}, clods {16}, max chassis impulse {17}, max landing {18} cm/s" -f $tag,$q.variant,$q.live,$q.target,$q.planned,$q.spawned,$q.no_ground,$q.candidate_m2,$q.density_scale,$q.breaks.wheel,$q.breaks.impulse,$q.breaks.landing,$q.lost,$q.deposited_cm3,$q.lost_cm3,$q.awake_peak,$q.clods,$q.max_chassis_impulse,$q.max_land_cm_s)}
    Write-Output ("MR5 {0}: world awake peak {1}, awake now {2}, capped {3}{4}" -f $tag,$t.awake_peak_world,$t.awake_now_world,$t.capped,$(if($t.error){" ERROR $($t.error)"}else{''}))}}
  if($m.cluster){Write-Output ("MR5 Standard's biggest cluster: {0} chunks at {1}, {2} cm (sizes {3}) of {4}" -f $m.cluster.count,$m.cluster.x_cm,$m.cluster.y_cm,($m.cluster.sizes_cm -join ' / '),$m.cluster.chunks_in_patch)}}
if(-not $report.ok){throw "Mud variants check failed (editor exit $code): $($report.error)"}
Write-Output 'MUD_VARIANTS_DRIVE_OK'

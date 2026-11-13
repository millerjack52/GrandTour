$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Living mud LM3a + LM3b + LM3c (docs/LIVE_SNOW_DRIVE.md): two passes of the real car down L_SnowDrive at full throttle (LM3c:
# no trials, the patch's own numbers), the pictures, the glint and border pixel counts, the berm's crest, the clods' luminance
# against the snow, Substrate's classification and a ProfileGPU dump per material, and the snow material's cost against the clay.
# LM4: Snow_GoW_View.png and Snow_OnFoot.png, the shards per pass (lip, floor, throw) and the plates that fell in, and the
# gt.Snow.FineGrid 1 / 0 pair in the same session (each its two passes and two cost-camera profiles; the mesh's triangles).
# LM4b: the GoW, on-foot and edge close-up pictures each with gt.Snow.Parallax 0 and 1, Snow_Edge_Mask.png, and the parallax
# pair's cost (the strip view and the edge view, 0 / 1 / 1 / 0).
# LM4c: the berm's crest out to 230 cm, the collapses per pass, and the collapse pair (Snow_Collapse_0s.png / _4s.png: a fresh
# cut at 90-99 m, 2.9 m to +Y, the same frame 0.2 s and 4 s after it).
# LM4d: Snow_Channel_Close.png (low along the belly's channel) and the channel's ridges, spill and clumps per pass.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW,GoWR -ErrorAction SilentlyContinue){throw 'Editor or game is running (GoWR, GoW and FarCry6 are checked)'}
# As the mud check: the editor's background throttle is off for this run (the run's own settings, nothing saved).
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-csvGpuStats','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-ExecutePythonScript="'+$root+'\Art\Unreal\check_live_snow_drive.py"'),('-abslog="'+$root+'\Saved\Logs\live_snow_drive.log"'))
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
$file=Get-Item "$root\Art\Export\LiveSnowDrive\drive-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No drive report written by this run (editor exit $code)"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw "Snow drive check failed (editor exit $code): $($report.error)"}
if($code -eq -1073741819){Write-Output 'Editor exit -1073741819 (0xC0000005) after the report: the known shutdown fault (LM0), not a check failure'}
elseif($code -ne 0){Write-Output "Editor exit $code after a fresh ok report (not judged)"}
Write-Output ("viewport: $($report.viewport_size -join 'x') (play: $($report.play_mode); first window $($report.viewport_retry -join 'x'), retried: $($report.play_mode_retry)); weather $($report.weather); sun toward $($report.sun_toward -join ', ')")
$pt=$report.patch
Write-Output ("patch (LM4): cell {0} cm, mesh {1} triangles, shards {2} ({3} meshes), plates {4}, wall steps {5} cm, drop share {6}, snow top undulation {7} cm" -f $pt.cell_cm,$pt.mesh_triangles,$pt.shards,$pt.clod_meshes,$pt.plates,($pt.wall_step_cm -join '-'),$pt.wall_drop_share,$pt.snow_top_undulation_cm)
Write-Output ("patch: {0}, {1}x{2} cells, box {3} - {4} (apron box matches: {5}), material {6} (parent {7}, LugTiltDeg {8}, GlintDensity {9}), clods {10}, snow {11} cm (at 50 m {12}, at the drift {13}, at 29 m {14}), SnowPlough {15}, SnowBellyDrag {16}, return {17}, sinkage {18} m" -f $pt.medium,$pt.cells[0],$pt.cells[1],($pt.bounds_min -join ','),($pt.bounds_max -join ','),$pt.apron_box_matches,$pt.material_path,$pt.mesh_material_parent,$pt.lug_tilt_deg,$pt.glint_density,$pt.clod_material,$pt.snow_depth_cm,$pt.snow_top_at_50m_cm,$pt.snow_top_at_drift_cm,$pt.snow_top_at_entry_cm,$pt.snow_plough,$pt.snow_belly_drag,$pt.ridge_return,$pt.profile_max_sinkage_m)
function Kmh($s){if($s){'{0:N1}' -f $s.kmh}else{'-'}}
# LM3b: the feel's trials (pass 1 in fresh snow at full throttle; targets A and B 8-15 km/h, drift 3-6 km/h, no stop over 1 s).
Write-Output 'trials (pass 1 in fresh snow, full throttle; A 40-66 m and B 85-110 m in 35 cm, the drift 70-80 m in 60 cm):'
Write-Output ('  {0,-17} {1,7} {2,7} {3,8} {4,8} {5,9} {6,10} {7,9} {8,8}  {9}' -f 'trial','plough','belly','A km/h','B km/h','35 km/h','drift km/h','stop s','landed','ended')
foreach($t in $report.trials){Write-Output ('  {0,-17} {1,7} {2,7} {3,8} {4,8} {5,9} {6,10} {7,9} {8,8}  {9}' -f $t.label,$t.plough,$t.belly,(Kmh $t.seg.A),(Kmh $t.seg.B),(Kmh $t.seg.'35cm'),(Kmh $t.seg.drift),$t.longest_stop_s,$t.landed,$t.ended)}
foreach($f in $report.fits){Write-Output ("  next: plough {0}, belly {1} ({2})" -f $f.plough,$f.belly,$f.why)}
$l=$report.landed
Write-Output ("landed on: SnowPlough {0}, SnowBellyDrag {1} (trial {2}, {3}; inside every band: {4}; the patch's own numbers: {5})" -f $l.plough,$l.belly,$l.trial,$l.label,$l.landed,$l.from_patch)
if($report.trials_skipped){Write-Output ("trials: {0}" -f $report.trials_skipped)}
foreach($r in $report.passes){
  Write-Output ("pass {0} (plough {1}, belly {2}): {3}; end {4:N2} m in {5:N1} s, completed {6}; max lateral {7} m over the snow; plough {8} cm^3 (berms {9}), lowered {10} cm^3" -f $r.npass,$r.plough,$r.belly,$r.ended,$r.end_x_m,$r.elapsed_s,$r.completed,$r.max_lateral_m,$r.plough_cm3,$r.plough_berm_cm3,$r.lowered_cm3)
  Write-Output ("pass {0} speeds: entry 30-66 m {1} km/h, A {2}, B {3}, the 35 cm outside the drift {4}, drift {5} km/h ({6} s, {7} m/s, min {8}); longest stop {9} s (at {10} m); feel targets met {11}" -f $r.npass,(Kmh $r.seg.entry),(Kmh $r.seg.A),(Kmh $r.seg.B),(Kmh $r.seg.'35cm'),(Kmh $r.seg.drift),$r.drift_s,$r.drift_mean_mps,$r.drift_min_mps,$r.longest_stop_s,$r.longest_stop_at_m,$r.feel_landed)
  Write-Output ("pass {0} drag (mean per wheel, fraction of load): A total {1}; drift total {2}, surface {3}, plough {4}, belly {5} (belly snow max {6} cm); friction scale {7}" -f $r.npass,$r.a_mean_rr,$r.drift_mean_rr,$r.drift_mean_surface,$r.drift_mean_plough,$r.drift_mean_belly,$r.drift_max_belly_snow_cm,$r.drift_mean_friction_scale)
  Write-Output ("pass {0} throw: {1} blobs, {2} through the Snow kind; landed {3} cm^3, lost {4} cm^3; clods live {5} (bank {6}, throw {7})" -f $r.npass,$r.throw_blobs,$r.throw_blobs_snow,$r.throw_landed_cm3,$r.throw_lost_cm3,$r.clods_live,$r.clods_bank,$r.clods_throw)
  if($r.settle){Write-Output ("pass {0}: settle {1} frames mean {2} / p99 {3} / max {4} ms (gate mean <= 0.3, p99 <= 0.7: {5}), awake peak {6}; upload mean {7} / p99 {8} / max {9} ms" -f $r.npass,$r.settle_frames,$r.settle.mean_ms,$r.settle.p99_ms,$r.settle.max_ms,$(if($r.settle.ok){'PASS'}else{'FAIL'}),$r.settle_awake_peak,$r.upload_mean_ms,$r.upload_p99_ms,$r.upload_max_ms)}
  Write-Output ("pass {0} [{1}, cell {2} cm]: shards {3}; live {4}: lip {5}, floor {6}, throw {7} (the field queued lip {8}, floor {9}); lip plates fallen in {10} ({11} cm^3 onto the floor)" -f $r.npass,$r.session,$r.cell_cm,$r.shards,$r.clods_live,$r.clods_bank,$r.clods_floor,$r.clods_throw,$r.lip_chunks_queued,$r.floor_chunks_queued,$r.wall_drops,$r.wall_drop_cm3)
  if($r.clods){Write-Output ("pass {0}: clods {1} frames mean {2} / p99 {3} / max {4} ms ({5}); refill passes {6}" -f $r.npass,$r.clod_frames,$r.clods.mean_ms,$r.clods.p99_ms,$r.clods.max_ms,$(if($r.clods.ok){'PASS'}else{'FAIL'}),$r.refill_passes)}
}
foreach($a in $report.profiles_across){foreach($t in $a.trenches){Write-Output ("profile after {0} at x {1} cm: snow top {2} cm; {3} trench floor {4} cm over the ground ({5} under the snow top), lip {6} cm over the snow top, wall step {7} cm = {8} deg; centre {9} cm over the ground" -f $a.after_pass,$a.x_cm,$a.snow_top_cm,$t.side,$t.floor_over_ground_cm,$t.floor_field_cm,$t.lip_over_snow_top_cm,$t.wall_step_cm,$t.wall_deg,$a.centre_over_ground_cm)}}
# LM3c item 3: the berm's crest along the trench on the strip (the A segment), per side.
foreach($bc in $report.berm_crest){foreach($side in @('-Y','+Y')){$c=$bc.$side;if($c){Write-Output ("berm crest after {0} ({1}-{2} cm, {3}-{4} cm off the line), {5}: {6} stations, mean {7} cm over the snow top, sd {8}, cv {9} (min {10}, max {11})" -f $bc.after_pass,$bc.x_cm[0],$bc.x_cm[1],$bc.y_off_cm[0],$bc.y_off_cm[1],$side,$c.stations,$c.mean_cm,$c.sd_cm,$c.cv,$c.min_cm,$c.max_cm);if($c.median_cm){Write-Output ("berm crest after {0}, {1}: median {2} cm, 90th percentile {3} cm (x{4}), highest {5} cm (x{6})" -f $bc.after_pass,$side,$c.median_cm,$c.p90_cm,$c.p90_x_median,$c.max_cm,$c.max_x_median)}}};Write-Output ("berm crest after {0}: cv mean of the two sides {1}" -f $bc.after_pass,$bc.cv_mean)}
if($report.berm_crest_error){Write-Output "berm crest error: $($report.berm_crest_error)"}
foreach($f in $report.profiles){Write-Output ("profile {0}: {1} frames, frame {2} / game {3} / GPU {4} ms mean, Basepass {5}, Prepass {6}, ShadowDepths {7}; GTMud Settle {8} / Clods {9} ms mean" -f $f.run,$f.frames,$f.FrameTime.mean,$f.GameThreadTime.mean,$f.GPUTime.mean,$f.'GPU/Basepass'.mean,$f.'GPU/Prepass'.mean,$f.'GPU/ShadowDepths'.mean,$f.'GTMud/GameThread/Settle'.mean,$f.'GTMud/GameThread/Clods'.mean)}
$cs=$report.cost_summary
if($cs){
  foreach($m in @('snow','clay','nosss')){$c=$cs.$m;if($c){Write-Output ("cost {0} on the patch ({1} frames, two 5 s profiles, ABCCBA): GPU/Basepass {2} ms, Prepass {3}, ShadowDepths {4}, GPU {5}, frame {6}" -f $m,$c.frames,$c.'GPU/Basepass',$c.'GPU/Prepass',$c.'GPU/ShadowDepths',$c.GPUTime,$c.FrameTime)}}
  foreach($k in @('snow_minus_clay','snow_minus_nosss')){$d=$cs.$k;if($d){Write-Output ("cost {0}: Basepass {1} ms, Prepass {2}, ShadowDepths {3}, GPU {4}, frame {5}" -f $k,$d.'GPU/Basepass',$d.'GPU/Prepass',$d.'GPU/ShadowDepths',$d.GPUTime,$d.FrameTime)}}
  foreach($k in @('passes_snow_minus_clay','passes_snow_minus_nosss')){$d=$cs.$k;if($d){Write-Output ("cost {0} (passes differing by 0.03 ms or more): {1}" -f $k,(($d.PSObject.Properties|ForEach-Object{"$($_.Name) $($_.Value)"}) -join ', '))}}
}
# LM3b: pixel counts in the pictures' boxes (the boxes are the check's projections of world rectangles), as
# Art/tools/sample_border.ps1 counts them: dark = the brightest channel under 40, sky-coloured = blue the brightest by 15
# or more over red, bright = the brightest channel over 245.
Add-Type -AssemblyName System.Drawing
function Measure-Box($png,$box){
  $bmp=[System.Drawing.Bitmap]::FromFile($png)
  try{
    $rect=New-Object System.Drawing.Rectangle(0,0,$bmp.Width,$bmp.Height)
    $data=$bmp.LockBits($rect,[System.Drawing.Imaging.ImageLockMode]::ReadOnly,[System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $stride=$data.Stride;$bytes=New-Object byte[] ($stride*$bmp.Height)
    [System.Runtime.InteropServices.Marshal]::Copy($data.Scan0,$bytes,0,$bytes.Length);$bmp.UnlockBits($data)
    $x0=[math]::Max(0,[int][math]::Floor([double]$box.x0));$y0=[math]::Max(0,[int][math]::Floor([double]$box.y0))
    $x1=[math]::Min($bmp.Width-1,[int][math]::Ceiling([double]$box.x1));$y1=[math]::Min($bmp.Height-1,[int][math]::Ceiling([double]$box.y1))
    $n=0;$dark=0;$sky=0;$bright=0;$white=0;$sum=0.0;$sr=0.0;$sg=0.0;$sb=0.0
    for($y=$y0;$y -le $y1;$y++){$row=$y*$stride;for($x=$x0;$x -le $x1;$x++){
      $i=$row+3*$x;$b=[int]$bytes[$i];$g=[int]$bytes[$i+1];$r=[int]$bytes[$i+2]
      $mx=[math]::Max($r,[math]::Max($g,$b));$mn=[math]::Min($r,[math]::Min($g,$b));$n++;$sum+=$mx;$sr+=$r;$sg+=$g;$sb+=$b
      if($mx -lt 40){$dark++};if($b -gt $r -and $b -gt $g -and ($b-$r) -ge 15){$sky++};if($mx -gt 245){$bright++};if($mn -gt 245){$white++}
    }}
    $k=[math]::Max(1,$n)
    return [pscustomobject]@{X0=$x0;Y0=$y0;X1=$x1;Y1=$y1;N=$n;Dark=$dark;Sky=$sky;Bright=$bright;White=$white;Mean=($sum/$k);R=($sr/$k);G=($sg/$k);B=($sb/$k)}
  } finally {$bmp.Dispose()}
}
$shots="$root\Art\Export\LiveSnowDrive"
# The boxes are projections in the PIE viewport; the pictures are 1440x900 with the camera's 16:9 frame letterboxed in
# both (the horizontal field of view kept), so a viewport shorter than the picture puts every box (900 - its height) / 2
# pixels higher than the picture has it.
$dy=0;if($report.viewport_size -and $report.viewport_size[1] -lt 900){$dy=(900-$report.viewport_size[1])/2}
foreach($prop in $report.boxes.PSObject.Properties){$b=$prop.Value;if($b){$b.y0=$b.y0+$dy;$b.y1=$b.y1+$dy}}
Write-Output ("boxes moved down {0} px (viewport {1}, pictures 1440x900)" -f $dy,($report.viewport_size -join 'x'))
$gb=$report.boxes.glint
if($gb){
  foreach($name in @('Snow_Glint','Snow_Glint_NoGlint')){
    $m=Measure-Box "$shots\$name.png" $gb
    Write-Output ("glint {0}: box {1},{2}-{3},{4} ({5} of {6} corners on screen), {7} px: brightest channel over 245 {8} ({9:P2}), all channels over 245 {10}; mean brightest {11:N1}, mean colour {12:N0} {13:N0} {14:N0}" -f $name,$m.X0,$m.Y0,$m.X1,$m.Y1,$gb.corners_on_screen,$gb.corners,$m.N,$m.Bright,($m.Bright/[math]::Max(1,$m.N)),$m.White,$m.Mean,$m.R,$m.G,$m.B)
  }
}
$bb=$report.boxes.border
if($bb){
  $m=Measure-Box "$shots\Snow_Border.png" $bb
  Write-Output ("border Snow_Border: box {0},{1}-{2},{3} ({4} of {5} corners on screen), {6} px: dark {7} ({8:P2}), sky-coloured {9} ({10:P2}), mean brightest {11:N1}, mean colour {12:N0} {13:N0} {14:N0}" -f $m.X0,$m.Y0,$m.X1,$m.Y1,$bb.corners_on_screen,$bb.corners,$m.N,$m.Dark,($m.Dark/[math]::Max(1,$m.N)),$m.Sky,($m.Sky/[math]::Max(1,$m.N)),$m.Mean,$m.R,$m.G,$m.B)
  $means=@{}
  foreach($strip in @('snowstrip','landstrip')){
    $sb=$report.boxes.$strip;if(-not $sb){continue}
    $s=Measure-Box "$shots\Snow_Border.png" $sb;$means[$strip]=$s.Mean
    Write-Output ("border {0} (3 x 1 m, 1.5 m {1} the box): {2} px, mean brightest {3:N1}, mean colour {4:N0} {5:N0} {6:N0}, dark {7}, sky-coloured {8}" -f $strip,$(if($strip -eq 'snowstrip'){'inside'}else{'outside'}),$s.N,$s.Mean,$s.R,$s.G,$s.B,$s.Dark,$s.Sky)
  }
  if($means.ContainsKey('snowstrip') -and $means.ContainsKey('landstrip')){Write-Output ("border: snow inside the box minus landscape outside it, mean brightest channel {0:N1}" -f ($means['snowstrip']-$means['landstrip']))}
  # The step at the edge itself (20 cm strips 10 cm either side), in the picture and in its two diagnostics.
  foreach($name in @('Snow_Border','Snow_Border_NoSSS','Snow_Border_NoSSS_F004')){
    if(-not (Test-Path "$shots\$name.png") -or -not $report.boxes.edge_in -or -not $report.boxes.edge_out){continue}
    $ein=Measure-Box "$shots\$name.png" $report.boxes.edge_in;$eout=Measure-Box "$shots\$name.png" $report.boxes.edge_out
    Write-Output ("edge {0}: 10-30 cm inside {1:N0} {2:N0} {3:N0} (brightest {4:N1}), 10-30 cm outside {5:N0} {6:N0} {7:N0} (brightest {8:N1}); inside minus outside R {9:N1} G {10:N1} B {11:N1}; dark {12}/{13}, sky-coloured {14}/{15}" -f $name,$ein.R,$ein.G,$ein.B,$ein.Mean,$eout.R,$eout.G,$eout.B,$eout.Mean,($ein.R-$eout.R),($ein.G-$eout.G),($ein.B-$eout.B),$ein.Dark,$eout.Dark,$ein.Sky,$eout.Sky)
  }
}
# LM3c item 4: the clods against the snow in Snow_Trench_Close.png. In each clod's projected box the clod's pixels are the
# ones the clods change (against Snow_Trench_Close_NoClods.png, the same frame with them hidden, by more than 12 levels in a
# channel); round it, a ring as wide as the box, the snow the clods leave alone (4 levels or less, other clods' boxes out).
# Sunlit: the brighter half of each (Rec. 709 luma of the 8-bit values); a clod counts as sunlit where its ring's brighter
# half reads 170 or more. The target: the sunlit clods' mean within 15 % of the sunlit snow round them.
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class GTPix
{
    public static byte[] Load(string path, out int w, out int h, out int stride)
    {
        using (Bitmap bmp = new Bitmap(path))
        {
            w = bmp.Width; h = bmp.Height;
            BitmapData data = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
            stride = data.Stride;
            byte[] bytes = new byte[stride * h];
            Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);
            bmp.UnlockBits(data);
            return bytes;
        }
    }
    static double Luma(byte[] a, int i) { return 0.2126 * a[i + 2] + 0.7152 * a[i + 1] + 0.0722 * a[i]; }
    static double TopHalf(List<double> v, out int n)
    {
        v.Sort(); n = v.Count - v.Count / 2; if (n <= 0) return 0;
        double s = 0; for (int k = v.Count / 2; k < v.Count; ++k) s += v[k]; return s / n;
    }
    // boxes: x0, y0, x1, y1 per clod; returns per clod: clod pixels, their top-half luma, ring pixels, their top-half luma, box pixels.
    public static double[] Clods(byte[] a, byte[] b, int w, int h, int stride, double[] boxes)
    {
        int count = boxes.Length / 4;
        double[] o = new double[count * 5];
        for (int c = 0; c < count; ++c)
        {
            double x0 = boxes[4 * c], y0 = boxes[4 * c + 1], x1 = boxes[4 * c + 2], y1 = boxes[4 * c + 3];
            double m = Math.Max(x1 - x0, y1 - y0);
            int rx0 = Math.Max(0, (int)Math.Floor(x0 - m)), ry0 = Math.Max(0, (int)Math.Floor(y0 - m));
            int rx1 = Math.Min(w - 1, (int)Math.Ceiling(x1 + m)), ry1 = Math.Min(h - 1, (int)Math.Ceiling(y1 + m));
            List<double> clod = new List<double>(), ring = new List<double>();
            int n = 0;
            for (int y = ry0; y <= ry1; ++y)
            {
                for (int x = rx0; x <= rx1; ++x)
                {
                    int i = y * stride + 3 * x;
                    int d = Math.Max(Math.Abs(a[i] - b[i]), Math.Max(Math.Abs(a[i + 1] - b[i + 1]), Math.Abs(a[i + 2] - b[i + 2])));
                    bool inBox = x >= x0 && x <= x1 && y >= y0 && y <= y1;
                    if (inBox) { ++n; if (d > 12) clod.Add(Luma(a, i)); continue; }
                    bool other = false;
                    for (int k = 0; k < count && !other; ++k)
                        if (k != c && x >= boxes[4 * k] && x <= boxes[4 * k + 2] && y >= boxes[4 * k + 1] && y <= boxes[4 * k + 3]) other = true;
                    if (!other && d <= 4) ring.Add(Luma(a, i));
                }
            }
            int cn, rn;
            double cl = TopHalf(clod, out cn), rl = TopHalf(ring, out rn);
            o[5 * c] = clod.Count; o[5 * c + 1] = cl; o[5 * c + 2] = ring.Count; o[5 * c + 3] = rl; o[5 * c + 4] = n;
        }
        return o;
    }
    // Every step-th pixel each way: Substrate's tile overlay colours (green Simple, yellow Single, red Complex, purple ComplexSpecial) and the rest.
    public static int[] Classify(byte[] a, int w, int h, int stride, int step)
    {
        int[] o = new int[5];
        for (int y = 0; y < h; y += step)
            for (int x = 0; x < w; x += step)
            {
                int i = y * stride + 3 * x; int B = a[i], G = a[i + 1], R = a[i + 2];
                if (G > 140 && R < 0.6 * G && B < 0.6 * G) o[0]++;
                else if (R > 140 && G > 140 && B < 0.6 * Math.Min(R, G)) o[1]++;
                else if (R > 140 && G < 0.5 * R && B < 0.5 * R) o[2]++;
                else if (R > 50 && B > 50 && G < 0.5 * Math.Min(R, B)) o[3]++;
                else o[4]++;
            }
        return o;
    }
}
"@
$cb=@($report.boxes_clods)
if($cb.Count -gt 0 -and (Test-Path "$shots\Snow_Trench_Close.png") -and (Test-Path "$shots\Snow_Trench_Close_NoClods.png")){
  $w=0;$h=0;$st=0;$w2=0;$h2=0;$st2=0
  $imgA=[GTPix]::Load("$shots\Snow_Trench_Close.png",[ref]$w,[ref]$h,[ref]$st)
  $imgB=[GTPix]::Load("$shots\Snow_Trench_Close_NoClods.png",[ref]$w2,[ref]$h2,[ref]$st2)
  $flat=New-Object double[] ($cb.Count*4)
  for($k=0;$k -lt $cb.Count;$k++){$flat[4*$k]=[double]$cb[$k].x0;$flat[4*$k+1]=[double]$cb[$k].y0+$dy;$flat[4*$k+2]=[double]$cb[$k].x1;$flat[4*$k+3]=[double]$cb[$k].y1+$dy}
  $res=[GTPix]::Clods($imgA,$imgB,$w,$h,$st,$flat)
  $litC=0.0;$litS=0.0;$litN=0;$shC=0.0;$shS=0.0;$shN=0;$seen=0;$ratios=@()
  for($k=0;$k -lt $cb.Count;$k++){
    $cn=$res[5*$k];$cl=$res[5*$k+1];$rn=$res[5*$k+2];$rl=$res[5*$k+3];$bn=$res[5*$k+4]
    if($cn -lt 8 -or $rn -lt 16){continue};$seen++
    if($rl -ge 170){$litC+=$cl;$litS+=$rl;$litN++;$ratios+=($cl/$rl)}else{$shC+=$cl;$shS+=$rl;$shN++}
  }
  Write-Output ("clods in Snow_Trench_Close: {0} live, {1} boxes on screen within 15 m (the nearest kept), {2} with 8 or more changed pixels and a ring" -f $report.clods_live_at_close,$cb.Count,$seen)
  if($litN -gt 0){
    $ratio=$litC/$litS;$med=($ratios|Sort-Object)[[int][math]::Floor($ratios.Count/2)]
    Write-Output ("clods sunlit: {0}; the clods' brighter half {1:N1}, the snow round them {2:N1} (luma, 0-255): clod / snow {3:N3} (median of the clods {4:N3}); asked within 15 %: {5}" -f $litN,($litC/$litN),($litS/$litN),$ratio,$med,$(if([math]::Abs($ratio-1) -le 0.15){'PASS'}else{'FAIL'}))
  } else {Write-Output 'clods sunlit: none of the boxes had a sunlit ring (unchecked)'}
  if($shN -gt 0){Write-Output ("clods in shade (ring under 170): {0}; the clods' brighter half {1:N1}, the snow round them {2:N1}: clod / snow {3:N3}" -f $shN,($shC/$shN),($shS/$shN),($shC/$shS))}
} else {Write-Output ("clods in Snow_Trench_Close: no boxes ({0})" -f $report.clod_boxes_error)}
# LM3c item 5: Substrate's classification overlay per material (every 4th pixel each way), and the ProfileGPU dumps' lighting lines.
foreach($name in @('Snow_Classify_Snow','Snow_Classify_Clay','Snow_Classify_Nosss')){
  if(-not (Test-Path "$shots\$name.png")){continue}
  $w=0;$h=0;$st=0;$img=[GTPix]::Load("$shots\$name.png",[ref]$w,[ref]$h,[ref]$st);$c=[GTPix]::Classify($img,$w,$h,$st,4);$t=[math]::Max(1,($c|Measure-Object -Sum).Sum)
  Write-Output ("classification {0}: green (Simple) {1:P1}, yellow (Single) {2:P1}, red (Complex) {3:P1}, purple (ComplexSpecial) {4:P1}, other {5:P1} of {6} samples" -f $name,($c[0]/$t),($c[1]/$t),($c[2]/$t),($c[3]/$t),($c[4]/$t),$t)
}
$logLines=Get-Content "$root\Saved\Logs\live_snow_drive.log" -ErrorAction SilentlyContinue
$inDump=$null;$dumpLines=@{}
foreach($line in $logLines){
  if($line -match 'LM3C_PROFILEGPU_BEGIN (\w+)'){$inDump=$Matches[1];$dumpLines[$inDump]=@();continue}
  if($line -match 'LM3C_PROFILEGPU_END'){$inDump=$null;continue}
  if($inDump -and $line -match 'StandardDeferred|DeferredLighting|DirectLighting|ClassificationPass|Lights|Substrate'){$dumpLines[$inDump]+=($line -replace '^.*?LogRHI: Display: ','')}
}
foreach($k in $dumpLines.Keys){$n=0;foreach($line in $dumpLines[$k]){if($n -ge 14){break};Write-Output ("profilegpu {0}: {1}" -f $k,$line.Substring(0,[math]::Min(200,$line.Length)).TrimEnd());$n++};if($dumpLines[$k].Count -eq 0){Write-Output "profilegpu ${k}: no lighting lines between the markers"}}
# LM4: the FineGrid pair - the mesh per session, the passes' Settle / upload p99 and CSV means, the cost camera's profiles.
foreach($gs in $report.grid){Write-Output ("grid {0} (gt.Snow.FineGrid {1}): cell {2} cm, {3}x{4} cells, mesh {5} vertices / {6} triangles, shards {7}" -f $gs.label,$gs.fine_grid,$gs.cell_cm,$gs.cells[0],$gs.cells[1],$gs.mesh_vertices,$gs.mesh_triangles,$gs.shards)}
foreach($r in $report.passes){$pf=$report.profiles|Where-Object{$_.run -eq $(if($r.session -eq 'main'){"pass$($r.npass)"}else{"$($r.session)_pass$($r.npass)"})}|Select-Object -First 1
  if($r.settle){Write-Output ("grid pass [{0}] {1}: settle p99 {2} ms (mean {3}), upload p99 {4} ms (mean {5}); CSV game thread {6} / GPU {7} / frame {8} ms mean; drift {9} m/s" -f $r.session,$r.npass,$r.settle.p99_ms,$r.settle.mean_ms,$r.upload_p99_ms,$r.upload_mean_ms,$pf.GameThreadTime.mean,$pf.GPUTime.mean,$pf.FrameTime.mean,$r.drift_mean_mps)}}
$gsum=$report.grid_summary
if($gsum){foreach($k in @('main','coarse','fine')){$c=$gsum.$k;if($c){Write-Output ("grid cost camera [{0}] ({1} profiles, {2} frames): GPU {3} ms, game thread {4}, frame {5}, Basepass {6}, ShadowDepths {7}" -f $k,$c.profiles,$c.frames,$c.GPUTime,$c.GameThreadTime,$c.FrameTime,$c.'GPU/Basepass',$c.'GPU/ShadowDepths')}}}
# LM4b: the parallax pair per view (the means of its two profiles at each setting) and 1 - 0.
$px=$report.parallax_summary
if($px){foreach($v in @('strip','edge')){$c=$px.$v;if($c){foreach($k in @('0','1')){$e=$c.$k;if($e){Write-Output ("parallax [{0}] gt.Snow.Parallax {1} ({2} profiles, {3} frames): GPU {4} ms, game thread {5}, frame {6}, Basepass {7}" -f $v,$k,$e.profiles,$e.frames,$e.GPUTime,$e.GameThreadTime,$e.FrameTime,$e.'GPU/Basepass')}};$d=$c.on_minus_off;if($d){Write-Output ("parallax [{0}] 1 - 0: GPU {1} ms, game thread {2}, frame {3}, Basepass {4}" -f $v,$d.GPUTime,$d.GameThreadTime,$d.FrameTime,$d.'GPU/Basepass')}}}}
# LM4c: the collapses per pass, and the collapse pair.
foreach($ps in $report.passes){if($null -ne $ps.smear_cm3){Write-Output ("channel after {0}: smear ridges {1} cm^3, spill {2} cm^3, {3} spill clumps queued, {4} channel clumps spawned" -f $ps.label,$ps.smear_cm3,$ps.spill_cm3,$ps.spill_clumps_queued,$ps.clods_channel)}}
foreach($ps in $report.passes){if($null -ne $ps.collapses_fired){Write-Output ("collapses after {0}: {1} fell ({2} cm^3), {3} segments armed, {4} clumps queued" -f $ps.label,$ps.collapses_fired,$ps.collapse_cm3,$ps.collapse_segs_armed,$ps.collapse_clumps_queued)}}
$cp=$report.collapse_pair
if($cp){Write-Output ("collapse pair: the cut at y {0} cm, x {1}; {2} segments armed (x, y, side, delay): {3}; chosen {4}; {5} fell between the two pictures; camera {6} -> {7}" -f $cp.cut_y_cm,($cp.cut_x_cm -join '-'),@($cp.segments).Count,(($cp.segments|ForEach-Object{'('+($_ -join ', ')+')'}) -join ' '),($cp.chosen -join ', '),$cp.fired_between,($cp.camera.location -join ', '),($cp.camera.target -join ', '))}
foreach($cam in @('gow_camera','onfoot_camera','edge_camera','channel_camera')){$c=$report.$cam;if($c){Write-Output ("{0}: location {1}, target {2}, fov {3}" -f $cam,($c.location -join ', '),($c.target -join ', '),$c.fov)}}
$g=$report.gates
Write-Output ("gates: both completed {0}; drift pass 2 / pass 1 = {1} (asked >= 1.15: {2}); pass 1 feel targets met {3}; cost {4}" -f $g.both_completed,$g.drift_ratio,$(if($g.drift_ratio_ok){'PASS'}else{'FAIL'}),$g.feel_pass1_landed,$(if($g.cost_ok){'PASS'}else{'FAIL'}))
foreach($i in $report.images){Write-Output "picture: $i"}
Write-Output 'LIVE_SNOW_DRIVE_OK'

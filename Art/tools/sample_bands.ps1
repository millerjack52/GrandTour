# Look stage L2 (docs/LOOK_PLAN.md, VEHICLE_BUILD_SYSTEM 56): the band pass's pictures, before and after. Per picture and
# box, on sample_tones.ps1's pattern: the pixel count, the mean colour (8-bit sRGB as the picture holds it), the distinct
# tones - colours quantised to 5 bits a channel (32 levels) holding over -Share of the box (0.5 %) - with the total count of
# 5-bit colours beside it, the top tones by share, and a 16-bin luminance histogram (Rec. 709 luma of the 8-bit values, 16
# levels a bin). Each picture is read twice: from -Before (the pictures copied aside before L2 was built) and from the live
# folder the .bat writes (or -After); the lines pair up, before first.
# The boxes: three per picture - sky, car (a panel of the car: the driven car's rear in hide_1 and hide_6, the painted car
# copy SM_TestCar in proving_09, where the box is the proving runner's logged "step 4: borderbox proving_09.../TestCar"
# line) and ground - plus water in hide_22 (the ford's sheet: its translucency is composited after the band pass) and the
# rally road in hide_10, and (Look L6) the near rally post in hide_10 (its middle, x 722-731, y 322-392). The Hide's boxes are fixed pixel rectangles picked from a look at the before pictures (1280 x 720);
# pictures with no car in frame (hide_10, hide_13, hide_22) have no car box.
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_bands.ps1
#   ... sample_bands.ps1 -Before Saved\Screenshots\L2_before -After Saved\Screenshots\L2_after -Only hide_1_valley
# -After defaults to the live folders; the "after" box lines read the live logs (Saved\Logs\hide_shots.log and
# proving_shots.log), the "before" ones Saved\Logs\L2\<log>_before.log.
# Look stage L6 (VEHICLE_BUILD_SYSTEM 57): -Dressing reads Art\dressing_shots.bat's pictures instead (Saved\Screenshots\M6\
# dress_<kind>_<off|on|on_base|off_base|plain>.png, the boxes from Saved\Logs\hide_shots.log's "borderbox dress_<kind>/<kind>"
# lines): per kind and picture the same tones and histogram plus the histogram's peaks (local maxima over 5 % of the box)
# and the grain - tone steps (the luma moved over 3 of 255 from the last counted tone) per 100 px along three rows at 30, 50
# and 70 % of the box's height; then the compose check - per pixel log2(luma(look) / luma(BaseColor view)) in bins of 0.05, the
# clusters (runs of bins each over 1 % of the pixels) holding over 5 % counted, off and on: the same count means the
# painted surface is lit into the same bands; and plain vs off - the mean absolute difference per channel and the share
# of pixels differing by more than 8 in any channel (what the game drew before L6), and the stone's twin cube, Surface 0
# against MI_Env_Greybox (the switch's 0 against the plain graph).
#   ... sample_bands.ps1 -Dressing        (-Kinds stone,post -Folder Saved\Screenshots\M6 -LogName hide_shots.log)
# Look stage L3 (VEHICLE_BUILD_SYSTEM 58): -Sky reads Art\sky_shots.bat's pictures (sky_<s|r|c>_<weather>_<switch>.png) and
# the logged "borderbox sky_<spot>/<box>" lines (-Ridge: a fixed box on hide_10's far ridge; -SkyCar: the tailgate in sky_s): per box the mean, tones, peaks,
# the mean saturation and blue - red, the cloud share and count on a sky box, the grain on the clump; then all on against
# each switch at 0 and against all on again (the noise), mean |difference| a channel.
#   ... sample_bands.ps1 -Sky            (-Ridge 220,315,420,324 -CloudSat 0.10 -CloudLuma 150)
param([string]$Before = "Saved\Screenshots\L2_before", [string]$After = "Saved\Screenshots", [string[]]$Only = @(), [double]$Share = 0.005,
      [switch]$Dressing, [string[]]$Kinds = @("stone", "post", "rock"), [string]$Folder = "Saved\Screenshots\M6", [string]$LogName = "hide_shots.log",
      [switch]$Sky, [int[]]$Ridge = @(220, 315, 420, 324), [int[]]$SkyCar = @(500, 632, 770, 704), [double]$CloudSat = 0.10, [double]$CloudLuma = 150)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System; using System.Collections.Generic; using System.Drawing; using System.Drawing.Imaging; using System.Runtime.InteropServices;
public static class GTBands {
    // Returns: n, mean r g b, the 5-bit colour counts (key = r5 << 10 | g5 << 5 | b5), the 16-bin luma histogram.
    public static object[] Measure(Bitmap bmp, int x0, int y0, int x1, int y1) {
        x0 = Math.Max(0, x0); y0 = Math.Max(0, y0); x1 = Math.Min(bmp.Width - 1, x1); y1 = Math.Min(bmp.Height - 1, y1);
        var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
        var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        var bytes = new byte[data.Stride * bmp.Height];
        Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);
        bmp.UnlockBits(data);
        var counts = new Dictionary<int, int>(); var hist = new int[16];
        long n = 0; double sr = 0, sg = 0, sb = 0;
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            int i = y * data.Stride + x * 3; int b = bytes[i], g = bytes[i + 1], r = bytes[i + 2];
            n++; sr += r; sg += g; sb += b;
            int key = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
            int c; counts.TryGetValue(key, out c); counts[key] = c + 1;
            double luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            hist[Math.Min(15, (int)Math.Floor(luma / 16))]++;
        }
        double n1 = Math.Max(1, n);
        return new object[] { n, sr / n1, sg / n1, sb / n1, counts, hist, x0, y0, x1, y1 };
    }
}
"@

if ($Sky) {
    # Look stage L3 (VEHICLE_BUILD_SYSTEM 58): Art\sky_shots.bat's pictures, Saved\Screenshots\M6\sky_<s|r|c>_<weather>_<switch>.png,
    # the boxes from Saved\Logs\hide_shots.log's "borderbox sky_<spot>/<box>" lines (and -Ridge, a fixed box on hide_10's far
    # ridge picked from a look). Per picture and box: the mean, the tones and the histogram's peaks as -Dressing, the mean
    # saturation ((max - min) / max of the 8-bit channels) and the mean blue - red, the grain on the clump; on a sky box the
    # cloud share (pixels with a saturation under -CloudSat and a luma over -CloudLuma) and the clouds (4-connected runs of
    # such pixels over 30 px). Then the pairs: each box's mean |difference| a channel, all on against Sky 0, Haze 0,
    # Foliage 0 and against all on again (the noise), per weather.
    Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System; using System.Collections.Generic; using System.Drawing; using System.Drawing.Imaging; using System.Runtime.InteropServices;
public static class GTSky {
    static byte[] Bytes(Bitmap bmp, out int stride) {
        var data = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        stride = data.Stride; var bytes = new byte[data.Stride * bmp.Height];
        Marshal.Copy(data.Scan0, bytes, 0, bytes.Length); bmp.UnlockBits(data); return bytes;
    }
    // mean saturation, mean blue - red, cloud share, cloud count
    public static double[] Stats(Bitmap bmp, int x0, int y0, int x1, int y1, double satMax, double lumaMin) {
        int stride; var p = Bytes(bmp, out stride);
        x0 = Math.Max(0, x0); y0 = Math.Max(0, y0); x1 = Math.Min(bmp.Width - 1, x1); y1 = Math.Min(bmp.Height - 1, y1);
        int w = x1 - x0 + 1, h = y1 - y0 + 1; var cloud = new bool[w * h];
        double ss = 0, sbr = 0; long n = 0, nc = 0;
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            int i = y * stride + x * 3; int b = p[i], g = p[i + 1], r = p[i + 2];
            int mx = Math.Max(r, Math.Max(g, b)), mn = Math.Min(r, Math.Min(g, b));
            double s = mx > 0 ? (double)(mx - mn) / mx : 0; ss += s; sbr += b - r; n++;
            double l = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            if (s < satMax && l > lumaMin) { cloud[(y - y0) * w + (x - x0)] = true; nc++; }
        }
        int blobs = 0; var seen = new bool[w * h]; var stack = new Stack<int>();
        for (int k = 0; k < w * h; k++) {
            if (!cloud[k] || seen[k]) continue;
            int size = 0; stack.Push(k); seen[k] = true;
            while (stack.Count > 0) {
                int q = stack.Pop(); size++; int qx = q % w, qy = q / w;
                if (qx > 0 && cloud[q - 1] && !seen[q - 1]) { seen[q - 1] = true; stack.Push(q - 1); }
                if (qx < w - 1 && cloud[q + 1] && !seen[q + 1]) { seen[q + 1] = true; stack.Push(q + 1); }
                if (qy > 0 && cloud[q - w] && !seen[q - w]) { seen[q - w] = true; stack.Push(q - w); }
                if (qy < h - 1 && cloud[q + w] && !seen[q + w]) { seen[q + w] = true; stack.Push(q + w); }
            }
            if (size > 30) blobs++;
        }
        double n1 = Math.Max(1, n);
        return new double[] { ss / n1, sbr / n1, nc / n1, blobs };
    }
    public static double[] Diff(Bitmap one, Bitmap two, int x0, int y0, int x1, int y1) {
        int s1, s2; var a = Bytes(one, out s1); var b = Bytes(two, out s2); double sum = 0; long big = 0, n = 0;
        x0 = Math.Max(0, x0); y0 = Math.Max(0, y0); x1 = Math.Min(one.Width - 1, x1); y1 = Math.Min(one.Height - 1, y1);
        double[] d3 = new double[3];
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            int i = y * s1 + x * 3, j = y * s2 + x * 3; int m = 0;
            for (int c = 0; c < 3; c++) { int d = a[i + c] - b[j + c]; d3[c] += d; sum += Math.Abs(d); m = Math.Max(m, Math.Abs(d)); }
            if (m > 8) big++; n++;
        }
        double n1 = Math.Max(1, n);
        // mean |difference| a channel, share over 8, the mean signed difference r g b (one - two)
        return new double[] { sum / (3 * n1), big / n1, d3[2] / n1, d3[1] / n1, d3[0] / n1 };
    }
    public static double Grain(Bitmap bmp, int x0, int y0, int x1, int y1) {
        int stride; var p = Bytes(bmp, out stride); double sum = 0; int rows = 0;
        foreach (double f in new double[] { 0.3, 0.5, 0.7 }) {
            int y = (int)Math.Round(y0 + (y1 - y0) * f); int changes = 0; int i0 = y * stride + x0 * 3;
            double tone = 0.2126 * p[i0 + 2] + 0.7152 * p[i0 + 1] + 0.0722 * p[i0];
            for (int x = x0 + 1; x <= x1; x++) { int i = y * stride + x * 3; double l = 0.2126 * p[i + 2] + 0.7152 * p[i + 1] + 0.0722 * p[i]; if (Math.Abs(l - tone) > 3.0) { changes++; tone = l; } }
            sum += 100.0 * changes / Math.Max(1, x1 - x0); rows++;
        }
        return sum / rows;
    }
}
"@
    function Tone-Text($key) {
        $k = [int]$key
        return "#{0:X2}{1:X2}{2:X2}" -f ((($k -shr 10) -band 31) * 8 + 4), ((($k -shr 5) -band 31) * 8 + 4), (($k -band 31) * 8 + 4)
    }
    $logPath = Join-Path $root ("Saved\Logs\" + $LogName)
    $dir = Join-Path $root $Folder
    "sky pictures in {0}, boxes from {1} ({2}); cloud: saturation under {3}, luma over {4}" -f $dir, $logPath, (Get-Item $logPath).LastWriteTime, $CloudSat, $CloudLuma
    $spots = [ordered]@{ s = @("sky", "car", "ground"); r = @("sky", "ridge", "car", "ground", "road"); c = @("clump", "car") }
    foreach ($spot in $spots.Keys) {
        $boxes = [ordered]@{}
        foreach ($name in $spots[$spot]) {
            if ($spot -eq "r" -and $name -eq "ridge") { $boxes[$name] = $Ridge; continue }
            if ($spot -eq "s" -and $name -eq "car") { $boxes[$name] = $SkyCar; continue }   # the tailgate, picked from a look (the logged box takes the ground beside it)
            $m = Select-String -Path $logPath -Pattern ("borderbox sky_" + $spot + "/" + $name + " ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d+)") | Select-Object -Last 1
            if (-not $m) { "sky_{0} {1}: no logged box" -f $spot, $name; continue }
            $g = $m.Matches[0].Groups
            $bb = @([int][math]::Floor([double]$g[1].Value), [int][math]::Floor([double]$g[2].Value), [int][math]::Ceiling([double]$g[3].Value), [int][math]::Ceiling([double]$g[4].Value))
            if ([int]$g[5].Value -lt 2 -or $bb[2] -le $bb[0] -or $bb[3] -le $bb[1] -or $bb[0] -ge 1280 -or $bb[1] -ge 720 -or $bb[2] -lt 0 -or $bb[3] -lt 0) { "sky_{0} {1}: the logged box {2} is off the screen or empty: left out" -f $spot, $name, ($bb -join ","); continue }
            $boxes[$name] = $bb
        }
        $bmps = [ordered]@{}
        Get-ChildItem -Path $dir -Filter ("sky_" + $spot + "_*.png") | Sort-Object Name | ForEach-Object { $bmps[$_.BaseName.Substring(6)] = [System.Drawing.Bitmap]::FromFile($_.FullName) }
        foreach ($state in $bmps.Keys) {
            foreach ($name in $boxes.Keys) {
                $b = $boxes[$name]
                $r = [GTBands]::Measure($bmps[$state], $b[0], $b[1], $b[2], $b[3])
                $n = [long]$r[0]; $counts = $r[4]; $hist = $r[5]
                $tones = @($counts.GetEnumerator() | Where-Object { $_.Value -gt $Share * $n } | Sort-Object Value -Descending)
                $top = ($tones | Select-Object -First 4 | ForEach-Object { "{0}:{1:P1}" -f (Tone-Text $_.Key), ($_.Value / [math]::Max(1, $n)) }) -join " "
                $peaks = 0
                for ($i = 0; $i -lt 16; $i++) {
                    $left = if ($i -gt 0) { $hist[$i - 1] } else { -1 }; $right = if ($i -lt 15) { $hist[$i + 1] } else { -1 }
                    if ($hist[$i] -gt 0.05 * $n -and $hist[$i] -ge $left -and $hist[$i] -ge $right) { $peaks++ }
                }
                $st = [GTSky]::Stats($bmps[$state], $b[0], $b[1], $b[2], $b[3], $CloudSat, $CloudLuma)
                $extra = ""
                if ($name -eq "sky") { $extra = "; cloud {0:P1}, {1} cloud(s)" -f $st[2], $st[3] }
                if ($name -eq "clump") { $extra = "; grain {0:N1}/100 px" -f [GTSky]::Grain($bmps[$state], $b[0], $b[1], $b[2], $b[3]) }
                "sky_{0} {1,-17} {2,-6} {3},{4}-{5},{6}: mean {7:N1} {8:N1} {9:N1}; sat {10:N3} b-r {11:N1}; tones {12} ({13}); peaks {14}{15}; top {16}" -f `
                    $spot, $state, $name, $b[0], $b[1], $b[2], $b[3], $r[1], $r[2], $r[3], $st[0], $st[1], $tones.Count, $counts.Count, $peaks, $extra, $top
            }
        }
        foreach ($weather in @("clear", "overcast")) {
            $on = $weather + "_on"
            if (-not $bmps.Contains($on)) { continue }
            foreach ($other in @("sky0", "haze0", "fol0", "on2", "dab1")) {
                $key = $weather + "_" + $other
                if (-not $bmps.Contains($key)) { continue }
                $line = @()
                foreach ($name in $boxes.Keys) {
                    $b = $boxes[$name]
                    $d = [GTSky]::Diff($bmps[$on], $bmps[$key], $b[0], $b[1], $b[2], $b[3])
                    $line += ("{0} {1:N2} ({2:P1} >8; on-{3} {4:+0.00;-0.00} {5:+0.00;-0.00} {6:+0.00;-0.00})" -f $name, $d[0], $d[1], $other, $d[2], $d[3], $d[4])
                }
                "sky_{0} {1} vs {2}: mean |difference| a channel: {3}" -f $spot, $on, $key, ($line -join "; ")
            }
        }
        foreach ($k in @($bmps.Keys)) { $bmps[$k].Dispose() }
    }
    return
}

if ($Dressing) {
    Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System; using System.Drawing; using System.Drawing.Imaging; using System.Runtime.InteropServices;
public static class GTDress {
    static byte[] Bytes(Bitmap bmp, out int stride) {
        var data = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        stride = data.Stride; var bytes = new byte[data.Stride * bmp.Height];
        Marshal.Copy(data.Scan0, bytes, 0, bytes.Length); bmp.UnlockBits(data); return bytes;
    }
    static int Key(byte[] p, int i) { return ((p[i + 2] >> 3) << 10) | ((p[i + 1] >> 3) << 5) | (p[i] >> 3); }
    static double Luma(byte[] p, int i) { return 0.2126 * p[i + 2] + 0.7152 * p[i + 1] + 0.0722 * p[i]; }
    // Tone steps per 100 px along rows at 30, 50 and 70 % of the box: a step is counted where the luma has moved more
    // than 3 of 255 from the last counted tone (a hysteresis, so the tonemapper's dither on one flat tone counts nothing).
    public static double Grain(Bitmap bmp, int x0, int y0, int x1, int y1) {
        int stride; var p = Bytes(bmp, out stride); double sum = 0; int rows = 0;
        foreach (double f in new double[] { 0.3, 0.5, 0.7 }) {
            int y = (int)Math.Round(y0 + (y1 - y0) * f); int changes = 0; double tone = Luma(p, y * stride + x0 * 3);
            for (int x = x0 + 1; x <= x1; x++) { double l = Luma(p, y * stride + x * 3); if (Math.Abs(l - tone) > 3.0) { changes++; tone = l; } }
            sum += 100.0 * changes / Math.Max(1, x1 - x0); rows++;
        }
        return sum / rows;
    }
    // log2(luma look / luma base) in 80 bins of 0.05 from -3; pixels with a base luma under 16 are left out.
    public static int[] Ratio(Bitmap look, Bitmap bas, int x0, int y0, int x1, int y1, out int n) {
        int s1, s2; var a = Bytes(look, out s1); var b = Bytes(bas, out s2); var h = new int[80]; n = 0;
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            double lb = Luma(b, y * s2 + x * 3); if (lb < 16) continue;
            double la = Math.Max(0.5, Luma(a, y * s1 + x * 3));
            int bin = (int)Math.Floor((Math.Log(la / lb, 2) + 3.0) / 0.05); h[Math.Max(0, Math.Min(79, bin))]++; n++;
        }
        return h;
    }
    // Mean absolute difference per channel, and the share of pixels differing by more than 8 in any channel.
    public static double[] Diff(Bitmap one, Bitmap two, int x0, int y0, int x1, int y1) {
        int s1, s2; var a = Bytes(one, out s1); var b = Bytes(two, out s2); double sum = 0; long big = 0, n = 0;
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            int i = y * s1 + x * 3, j = y * s2 + x * 3; int m = 0;
            for (int c = 0; c < 3; c++) { int d = Math.Abs(a[i + c] - b[j + c]); sum += d; m = Math.Max(m, d); }
            if (m > 8) big++; n++;
        }
        return new double[] { sum / Math.Max(1, 3 * n), (double)big / Math.Max(1, n) };
    }
}
"@
    function Tone-Text($key) {
        $k = [int]$key
        return "#{0:X2}{1:X2}{2:X2}" -f ((($k -shr 10) -band 31) * 8 + 4), ((($k -shr 5) -band 31) * 8 + 4), (($k -band 31) * 8 + 4)
    }
    $logPath = Join-Path $root ("Saved\Logs\" + $LogName)
    $dir = Join-Path $root $Folder
    "dressing pictures in {0}, boxes from {1} ({2})" -f $dir, $logPath, (Get-Item $logPath).LastWriteTime
    "tones: 5-bit colours over {0:P1} of the box; histogram: 16 luma bins of 16 levels; peaks: local maxima over 5 %; grain: tone steps per 100 px" -f $Share
    foreach ($kind in $Kinds) {
        $pattern = "borderbox dress_" + $kind + "/" + $kind + " ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d+)"
        $m = Select-String -Path $logPath -Pattern $pattern | Select-Object -Last 1
        if (-not $m) { "{0,-6} no logged box" -f $kind; continue }
        $g = $m.Matches[0].Groups
        $b = @([int][math]::Floor([double]$g[1].Value), [int][math]::Floor([double]$g[2].Value), [int][math]::Ceiling([double]$g[3].Value), [int][math]::Ceiling([double]$g[4].Value))
        $bmps = @{}
        foreach ($state in @("off", "on", "on_base", "off_base", "plain")) {
            $png = Join-Path $dir ("dress_" + $kind + "_" + $state + ".png")
            if (Test-Path $png) { $bmps[$state] = [System.Drawing.Bitmap]::FromFile($png) } else { "{0,-6} {1,-8} missing {2}" -f $kind, $state, $png }
        }
        foreach ($state in @("off", "on", "plain", "on_base", "off_base")) {
            if (-not $bmps.ContainsKey($state)) { continue }
            $r = [GTBands]::Measure($bmps[$state], $b[0], $b[1], $b[2], $b[3])
            $n = [long]$r[0]; $counts = $r[4]; $hist = $r[5]
            $tones = @($counts.GetEnumerator() | Where-Object { $_.Value -gt $Share * $n } | Sort-Object Value -Descending)
            $top = ($tones | Select-Object -First 4 | ForEach-Object { "{0}:{1:P1}" -f (Tone-Text $_.Key), ($_.Value / [math]::Max(1, $n)) }) -join " "
            $peaks = 0
            for ($i = 0; $i -lt 16; $i++) {
                $left = if ($i -gt 0) { $hist[$i - 1] } else { -1 }; $right = if ($i -lt 15) { $hist[$i + 1] } else { -1 }
                if ($hist[$i] -gt 0.05 * $n -and $hist[$i] -ge $left -and $hist[$i] -ge $right) { $peaks++ }
            }
            $grain = [GTDress]::Grain($bmps[$state], $b[0], $b[1], $b[2], $b[3])
            "{0,-6} {1,-8} {2},{3}-{4},{5} ({6} px): mean {7:N1} {8:N1} {9:N1}; tones {10} ({11} colours); peaks {12}; grain {13:N1}/100 px; top {14}" -f `
                $kind, $state, $b[0], $b[1], $b[2], $b[3], $n, $r[1], $r[2], $r[3], $tones.Count, $counts.Count, $peaks, $grain, $top
            "{0,-6} {1,-8} histogram {2}" -f "", "", ($hist -join " ")
        }
        foreach ($pair in @(@("off", "off_base"), @("on", "on_base"))) {
            if (-not ($bmps.ContainsKey($pair[0]) -and $bmps.ContainsKey($pair[1]))) { continue }
            $n = 0
            $h = [GTDress]::Ratio($bmps[$pair[0]], $bmps[$pair[1]], $b[0], $b[1], $b[2], $b[3], [ref]$n)
            $clusters = @(); $i = 0
            while ($i -lt 80) {
                if ($h[$i] -gt 0.01 * $n) {
                    $j = $i; $sum = 0; $w = 0.0
                    while ($j -lt 80 -and $h[$j] -gt 0.01 * $n) { $sum += $h[$j]; $w += $h[$j] * (($j + 0.5) * 0.05 - 3.0); $j++ }
                    if ($sum -gt 0.05 * $n) { $clusters += ("x{0:N2}:{1:P0}" -f [math]::Pow(2, $w / $sum), ($sum / $n)) }
                    $i = $j
                } else { $i++ }
            }
            "{0,-6} compose {1,-4} look / BaseColor over {2} px: {3} cluster(s) over 5 % [{4}]" -f $kind, $pair[0], $n, $clusters.Count, ($clusters -join " ")
        }
        if ($bmps.ContainsKey("plain") -and $bmps.ContainsKey("off")) {
            $d = [GTDress]::Diff($bmps["plain"], $bmps["off"], $b[0], $b[1], $b[2], $b[3])
            "{0,-6} plain vs off: mean |difference| {1:N2} a channel, {2:P2} of the pixels differ by over 8" -f $kind, $d[0], $d[1]
        }
        # The stone's twin: a non-instanced cube in the Surface 0 instance and in MI_Env_Greybox, the same frame.
        $tm = Select-String -Path $logPath -Pattern ("borderbox dress_" + $kind + "/twin ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners") | Select-Object -Last 1
        $t0 = Join-Path $dir ("dress_" + $kind + "_twin_off.png"); $t1 = Join-Path $dir ("dress_" + $kind + "_twin_plain.png")
        if ($tm -and (Test-Path $t0) -and (Test-Path $t1)) {
            $tg = $tm.Matches[0].Groups
            $tb = @([int][math]::Floor([double]$tg[1].Value), [int][math]::Floor([double]$tg[2].Value), [int][math]::Ceiling([double]$tg[3].Value), [int][math]::Ceiling([double]$tg[4].Value))
            $ba = [System.Drawing.Bitmap]::FromFile($t0); $bb = [System.Drawing.Bitmap]::FromFile($t1)
            $d = [GTDress]::Diff($ba, $bb, $tb[0], $tb[1], $tb[2], $tb[3])
            $ra = [GTBands]::Measure($ba, $tb[0], $tb[1], $tb[2], $tb[3]); $rb = [GTBands]::Measure($bb, $tb[0], $tb[1], $tb[2], $tb[3])
            "{0,-6} twin {1},{2}-{3},{4}: Surface 0 mean {5:N1} {6:N1} {7:N1}, MI_Env_Greybox mean {8:N1} {9:N1} {10:N1}; mean |difference| {11:N2} a channel, {12:P2} of the pixels differ by over 8" -f `
                $kind, $tb[0], $tb[1], $tb[2], $tb[3], $ra[1], $ra[2], $ra[3], $rb[1], $rb[2], $rb[3], $d[0], $d[1]
            $ba.Dispose(); $bb.Dispose()
        }
        foreach ($k in $bmps.Keys) { $bmps[$k].Dispose() }
    }
    return
}

$fixed = [ordered]@{
    "hide_1_valley"             = [ordered]@{ sky = @(300, 20, 900, 120); car = @(540, 625, 760, 655); ground = @(200, 600, 460, 700) }
    "hide_6_bog"                = [ordered]@{ sky = @(300, 20, 900, 120); car = @(560, 315, 650, 350); ground = @(100, 520, 500, 700) }
    "hide_10_rally"             = [ordered]@{ sky = @(300, 20, 900, 150); ground = @(760, 450, 1240, 700); road = @(40, 440, 300, 640); post = @(722, 322, 731, 392) }
    "hide_13_rut_low"           = [ordered]@{ sky = @(650, 20, 1250, 100); ground = @(300, 570, 900, 700) }
    "hide_22_ford_bank"         = [ordered]@{ sky = @(300, 20, 900, 150); ground = @(1060, 250, 1270, 360); water = @(300, 450, 1000, 700) }
    "proving_09_painted_after"  = [ordered]@{ sky = @(300, 20, 900, 150); car = "TestCar"; ground = @(100, 450, 1200, 700) }
}
$folders = @{ "hide_1_valley" = "M6"; "hide_6_bog" = "M6"; "hide_10_rally" = "M6"; "hide_13_rut_low" = "M6"; "hide_22_ford_bank" = "M6"; "proving_09_painted_after" = "Proving" }
$logs = @{ "M6" = "hide_shots.log"; "Proving" = "proving_shots.log" }

function Get-LoggedBox($logPath, $name) {
    $pattern = "step 4: borderbox " + [regex]::Escape($name) + " ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d)"
    $m = Select-String -Path $logPath -Pattern $pattern | Select-Object -Last 1
    if (-not $m) { return $null }
    $g = $m.Matches[0].Groups
    return @([int][math]::Floor([double]$g[1].Value), [int][math]::Floor([double]$g[2].Value), [int][math]::Ceiling([double]$g[3].Value), [int][math]::Ceiling([double]$g[4].Value))
}

function Tone-Text($key) {
    $k = [int]$key
    $r = (($k -shr 10) -band 31) * 8 + 4; $gg = (($k -shr 5) -band 31) * 8 + 4; $b = ($k -band 31) * 8 + 4
    return "#{0:X2}{1:X2}{2:X2}" -f $r, $gg, $b
}

"tones: 5-bit-a-channel colours holding over {0:P1} of a box; histogram: 16 luminance bins of 16 levels, dark to light" -f $Share
foreach ($pic in $fixed.Keys) {
    if ($Only.Count -gt 0 -and -not ($Only -contains $pic)) { continue }
    $folder = $folders[$pic]
    foreach ($side in @("before", "after")) {
        $dir = if ($side -eq "before") { Join-Path $root ($Before + "\" + $folder) } else { Join-Path $root ($After + "\" + $folder) }
        $png = Join-Path $dir ($pic + ".png")
        if (-not (Test-Path $png)) { "{0,-25} {1,-6} missing picture {2}" -f $pic, $side, $png; continue }
        $logPath = if ($side -eq "before") { Join-Path $root ("Saved\Logs\L2\" + [IO.Path]::GetFileNameWithoutExtension($logs[$folder]) + "_before.log") } else { Join-Path $root ("Saved\Logs\" + $logs[$folder]) }
        $bmp = [System.Drawing.Bitmap]::FromFile($png)
        foreach ($box in $fixed[$pic].Keys) {
            $b = $fixed[$pic][$box]
            if ($b -is [string]) { $b = Get-LoggedBox $logPath ($pic + "/" + $b); if (-not $b) { "{0,-25} {1,-6} {2,-6} no logged box in {3}" -f $pic, $side, $box, $logPath; continue } }
            $r = [GTBands]::Measure($bmp, $b[0], $b[1], $b[2], $b[3])
            $n = [long]$r[0]; $counts = $r[4]
            $tones = @($counts.GetEnumerator() | Where-Object { $_.Value -gt $Share * $n } | Sort-Object Value -Descending)
            $top = ($tones | Select-Object -First 5 | ForEach-Object { "{0}:{1:P1}" -f (Tone-Text $_.Key), ($_.Value / [math]::Max(1, $n)) }) -join " "
            "{0,-25} {1,-6} {2,-6} {3},{4}-{5},{6} ({7} px): mean {8:N1} {9:N1} {10:N1}; tones {11} ({12} colours in all); top {13}" -f `
                $pic, $side, $box, $r[6], $r[7], $r[8], $r[9], $n, $r[1], $r[2], $r[3], $tones.Count, $counts.Count, $top
            "{0,-25} {1,-6} {2,-6} histogram {3}" -f "", "", "", ($r[5] -join " ")
        }
        $bmp.Dispose()
    }
}

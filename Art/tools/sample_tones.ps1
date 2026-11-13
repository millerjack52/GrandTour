# Mean colour and distinct tones in logged screen boxes (Look stage L1, docs/LOOK_PLAN.md, VEHICLE_BUILD_SYSTEM 55;
# L2 reuses it). The boxes are the runner's "step N: borderbox <picture>/<box> x0 y0 x1 y1 corners on screen k" lines
# (sample_border.ps1's format). Per picture and box: the pixel count, the mean colour (8-bit sRGB as the picture holds
# it), the distinct tones - colours quantised to 5 bits a channel (32 levels) holding over -Share of the box (0.5 %) -
# with the total count of 5-bit colours beside it, the top tones by share, and a 16-bin luminance histogram (Rec. 709
# luma of the 8-bit values, 16 levels a bin). Then, per box, after minus before for the mean colour.
# Default: L_Proving's step 4 (proving_shots.bat 4) - the painted props SM_TestBox and SM_TestCar in the plain grey
# material (proving_08_painted_before) and in their painted instances (proving_09_painted_after), and the parked car's
# side (control_car, M_GT_Vehicle in both, so its change is the exposure's, not the paint's). Look L1 follow-up 3: the
# car's own painted panels, car_FrontDoors and car_RearPanel (the owner's panel bakes on M_GT_Vehicle's UsePaint 1).
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_tones.ps1
#   ... sample_tones.ps1 -LogName hide_shots.log -Folder M6 -Step 12 -Names hide_13_x -Boxes somebox
param([string]$LogName = "proving_shots.log", [string]$Folder = "Proving", [int]$Step = 4,
      [string[]]$Names = @("proving_08_painted_before", "proving_09_painted_after"),
      [string[]]$Boxes = @("TestBox", "TestCar", "control_car", "car_FrontDoors", "car_RearPanel", "car_Bonnet", "car_Roof"),
      [double]$Share = 0.005)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root ("Saved\Logs\" + $LogName)
Add-Type -AssemblyName System.Drawing

function Get-Box($name) {
    $pattern = "step " + $Step + ": borderbox " + [regex]::Escape($name) + " ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d)"
    $m = Select-String -Path $log -Pattern $pattern | Select-Object -Last 1
    if (-not $m) { return $null }
    return $m.Matches[0].Groups
}

function Measure-Tones($bmp, $g) {
    $x0 = [math]::Max(0, [int][math]::Floor([double]$g[1].Value)); $y0 = [math]::Max(0, [int][math]::Floor([double]$g[2].Value))
    $x1 = [math]::Min($bmp.Width - 1, [int][math]::Ceiling([double]$g[3].Value)); $y1 = [math]::Min($bmp.Height - 1, [int][math]::Ceiling([double]$g[4].Value))
    $n = 0; $sr = 0.0; $sg = 0.0; $sb = 0.0
    $counts = @{}
    $hist = New-Object 'int[]' 16
    for ($y = $y0; $y -le $y1; $y++) { for ($x = $x0; $x -le $x1; $x++) {
        $c = $bmp.GetPixel($x, $y); $n++; $sr += $c.R; $sg += $c.G; $sb += $c.B
        $key = (([int]$c.R -shr 3) -shl 10) -bor (([int]$c.G -shr 3) -shl 5) -bor ([int]$c.B -shr 3)   # [int]: a Byte shifted stays a Byte
        if ($counts.ContainsKey($key)) { $counts[$key]++ } else { $counts[$key] = 1 }
        $luma = 0.2126 * $c.R + 0.7152 * $c.G + 0.0722 * $c.B
        $hist[[math]::Min(15, [int][math]::Floor($luma / 16))]++
    } }
    $n1 = [math]::Max(1, $n)
    $tones = @($counts.GetEnumerator() | Where-Object { $_.Value -gt $Share * $n } | Sort-Object Value -Descending)
    return [pscustomobject]@{ X0 = $x0; Y0 = $y0; X1 = $x1; Y1 = $y1; N = $n; R = $sr / $n1; G = $sg / $n1; B = $sb / $n1;
        Tones = $tones; All = $counts.Count; Hist = $hist }
}

function Tone-Text($key) {
    # a 5-bit key back to the middle of its 8-bit cell, as #RRGGBB
    $k = [int]$key
    $r = (($k -shr 10) -band 31) * 8 + 4; $gg = (($k -shr 5) -band 31) * 8 + 4; $b = ($k -band 31) * 8 + 4
    return "#{0:X2}{1:X2}{2:X2}" -f $r, $gg, $b
}

"tones: 5-bit-a-channel colours holding over {0:P1} of a box; histogram: 16 luminance bins of 16 levels, dark to light" -f $Share
$means = @{}
foreach ($name in $Names) {
    $png = Join-Path $root ("Saved\Screenshots\" + $Folder + "\" + $name + ".png")
    if (-not (Test-Path $png)) { "{0,-26} missing picture {1}" -f $name, $png; continue }
    $bmp = [System.Drawing.Bitmap]::FromFile($png)
    foreach ($box in $Boxes) {
        $g = Get-Box ($name + "/" + $box)
        if (-not $g) { "{0,-26} {1,-12} no borderbox line in {2}" -f $name, $box, $log; continue }
        $r = Measure-Tones $bmp $g
        $means[$name + "/" + $box] = @($r.R, $r.G, $r.B)
        "{0,-26} {1,-12} {2},{3}-{4},{5} ({6} px, corners on screen {7}): mean {8:N1} {9:N1} {10:N1}; tones {11} ({12} colours in all)" -f `
            $name, $box, $r.X0, $r.Y0, $r.X1, $r.Y1, $r.N, $g[5].Value, $r.R, $r.G, $r.B, $r.Tones.Count, $r.All
        $top = ($r.Tones | Select-Object -First 8 | ForEach-Object { "{0}:{1:P1}" -f (Tone-Text $_.Key), ($_.Value / [math]::Max(1, $r.N)) }) -join " "
        "{0,-26} {1,-12} top tones {2}" -f "", "", $top
        "{0,-26} {1,-12} histogram {2}" -f "", "", ($r.Hist -join " ")
    }
    $bmp.Dispose()
}
if ($Names.Count -ge 2) {
    foreach ($box in $Boxes) {
        $a = $means[$Names[0] + "/" + $box]; $b = $means[$Names[-1] + "/" + $box]
        if ($a -and $b) {
            "{0,-12} {1} minus {2}: mean {3:N1} {4:N1} {5:N1}" -f $box, $Names[-1], $Names[0], ($b[0] - $a[0]), ($b[1] - $a[1]), ($b[2] - $a[2])
        }
    }
}

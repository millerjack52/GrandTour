# Counts the dark pixels in the rut band's screen box (the "step 13: rutbox x0 y0 x1 y1" line of hide_shots.log) in the
# four eye-level pictures hide_shots takes of it: as shipped, with the slide-away offset off, with the mud mesh hidden,
# with the landscape's shadow off - and, since stage I, in hide_20_rut_side's own box (the "step 16: sidebox" line: the
# same band seen from beside it, 1.5 m up and 2 m to the side, looking along the ridge line).
# A pixel is dark when its brightest channel is under the threshold (a lit mud surface reads well over 100; a back face or a
# hole reads under 30). Prints, per picture, the box, the dark count and share, and the mean brightness, so a dark strip along
# the band is put down to its cause by numbers.   powershell -ExecutionPolicy Bypass -File Art\tools\sample_rut_low.ps1 [threshold]
param([int]$Threshold = 40)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root "Saved\Logs\hide_shots.log"
Add-Type -AssemblyName System.Drawing

function Sample-Box($name, $bx0, $by0, $bx1, $by1) {
    $png = Join-Path $root ("Saved\Screenshots\M6\" + $name + ".png")
    if (-not (Test-Path $png)) { "{0,-20} missing" -f $name; return }
    $bmp = [System.Drawing.Bitmap]::FromFile($png)
    $x0 = [math]::Max(0, [int][math]::Floor([double]$bx0)); $y0 = [math]::Max(0, [int][math]::Floor([double]$by0))
    $x1 = [math]::Min($bmp.Width - 1, [int][math]::Ceiling([double]$bx1)); $y1 = [math]::Min($bmp.Height - 1, [int][math]::Ceiling([double]$by1))
    $dark = 0; $n = 0; $sum = 0.0; $dr = 0; $dg = 0; $db = 0; $bins = @(0, 0, 0, 0, 0, 0)
    for ($y = $y0; $y -le $y1; $y++) { for ($x = $x0; $x -le $x1; $x++) {
        $c = $bmp.GetPixel($x, $y); $b = [math]::Max($c.R, [math]::Max($c.G, $c.B)); $n++; $sum += $b
        if ($b -lt $Threshold) { $dark++; $dr += $c.R; $dg += $c.G; $db += $c.B }
        if ($b -lt 40) { $bins[0]++ } elseif ($b -lt 100) { $bins[1]++ } elseif ($b -lt 160) { $bins[2]++ } elseif ($b -lt 200) { $bins[3]++ } elseif ($b -lt 235) { $bins[4]++ } else { $bins[5]++ }
    } }
    $d = [math]::Max(1, $dark)
    "{0,-20} {1}x{2} box {3},{4}-{5},{6}: dark {7} of {8} ({9:P1}) mean RGB {11:N0} {12:N0} {13:N0}, mean brightest channel {10:N1}" -f $name, $bmp.Width, $bmp.Height, $x0, $y0, $x1, $y1, $dark, $n, ($dark / [math]::Max(1, $n)), ($sum / [math]::Max(1, $n)), ($dr / $d), ($dg / $d), ($db / $d)
    # the spread: how many pixels sit below, within and above the lit ground's band (160-200 with nothing but the landscape in the box)
    "{0,-20} brightest channel <40: {1}  40-100: {2}  100-160: {3}  160-200: {4}  200-235: {5}  >=235: {6}" -f "", $bins[0], $bins[1], $bins[2], $bins[3], $bins[4], $bins[5]
    $bmp.Dispose()
}

$m = Select-String -Path $log -Pattern "step 13: rutbox ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d+)" | Select-Object -Last 1
if (-not $m) { "no rutbox line in $log" } else {
    $g = $m.Matches[0].Groups
    "rutbox {0} {1} {2} {3} (corners on screen {4}), dark = brightest channel under {5}" -f $g[1].Value, $g[2].Value, $g[3].Value, $g[4].Value, $g[5].Value, $Threshold
    foreach ($name in @("hide_13_rut_low", "hide_14_rut_slide", "hide_15_rut_nomesh", "hide_16_rut_noshadow")) {
        Sample-Box $name $g[1].Value $g[2].Value $g[3].Value $g[4].Value
    }
}

# Stage I: the same band from beside it (hide_20_rut_side), its own box from the runner's sidebox line.
$s = Select-String -Path $log -Pattern "step 16: sidebox ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d+)" | Select-Object -Last 1
if (-not $s) { "no sidebox line in $log" } else {
    $h = $s.Matches[0].Groups
    "sidebox {0} {1} {2} {3} (points on screen {4}), dark = brightest channel under {5}" -f $h[1].Value, $h[2].Value, $h[3].Value, $h[4].Value, $h[5].Value, $Threshold
    Sample-Box "hide_20_rut_side" $h[1].Value $h[2].Value $h[3].Value $h[4].Value
}

# Stage G: the same band and the same eye as hide_13, with the water table lifted by a wetness of 1 (hide_21_rut_wet),
# from the runner's wetbox line. Its 200-235 band against hide_13's is the sky standing in the ruts.
$w = Select-String -Path $log -Pattern "step 17: wetbox ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d+)" | Select-Object -Last 1
if (-not $w) { "no wetbox line in $log" } else {
    $k = $w.Matches[0].Groups
    "wetbox {0} {1} {2} {3} (corners on screen {4}), dark = brightest channel under {5}" -f $k[1].Value, $k[2].Value, $k[3].Value, $k[4].Value, $k[5].Value, $Threshold
    Sample-Box "hide_21_rut_wet" $k[1].Value $k[2].Value $k[3].Value $k[4].Value
}

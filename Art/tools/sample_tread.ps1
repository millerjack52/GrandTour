# Counts the tyre's lugs in hide_19_tread_top (docs/MUD_ONE_SURFACE_PLAN.md stage F), the picture hide_shots takes
# straight down from 3 m over one of the bog crawl's ruts. The runner logs the rut axis's two projected ends and how many
# lugs the mud field says lie along it ("step 15: treadaxis x0 y0 x1 y1 span ... expected N lugs"); this walks that line
# in the picture one pixel at a time, averaging across it, and counts the bright bands: a rising crossing of the mean
# (the lug tops catch the sun where the flanks do not). Expect the two counts within 2 of each other.
# The mean is a LOCAL one, a moving average over two and a half lug periods: a rut's own shape swings the brightness by
# 150 levels from floor to rim over tens of pixels, so a lug riding on that never crosses the picture's global mean.
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_tread.ps1 [halfwidth]
param([int]$HalfWidth = 3)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root "Saved\Logs\hide_shots.log"
Add-Type -AssemblyName System.Drawing
$m = Select-String -Path $log -Pattern "step 15: treadaxis ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) span ([\d.\-]+) cm lug ([\d.\-]+) cm expected ([\d.\-]+) lugs, ends on screen (\d)" | Select-Object -Last 1
if (-not $m) { "no treadaxis line in $log"; exit 1 }
$g = $m.Matches[0].Groups
$x0 = [double]$g[1].Value; $y0 = [double]$g[2].Value; $x1 = [double]$g[3].Value; $y1 = [double]$g[4].Value
$span = [double]$g[5].Value; $lug = [double]$g[6].Value; $expected = [double]$g[7].Value
"treadaxis {0:N0},{1:N0} to {2:N0},{3:N0}: {4:N0} cm of rut, LugPeriodCm {5:N1}, the field says {6:N1} lugs (ends on screen {7})" -f $x0, $y0, $x1, $y1, $span, $lug, $expected, $g[8].Value
$png = Join-Path $root "Saved\Screenshots\M6\hide_19_tread_top.png"
if (-not (Test-Path $png)) { "hide_19_tread_top missing"; exit 1 }
$bmp = [System.Drawing.Bitmap]::FromFile($png)
$dx = $x1 - $x0; $dy = $y1 - $y0
$len = [math]::Sqrt($dx * $dx + $dy * $dy)
if ($len -lt 20) { "the axis is only {0:N0} px long: nothing to sample" -f $len; $bmp.Dispose(); exit 1 }
$ux = $dx / $len; $uy = $dy / $len
$px = -$uy; $py = $ux          # across the rut, for the averaging band
$steps = [int][math]::Floor($len)
$profile = New-Object double[] ($steps + 1)
for ($i = 0; $i -le $steps; $i++) {
    $sum = 0.0; $n = 0
    for ($w = -$HalfWidth; $w -le $HalfWidth; $w++) {
        $sx = [int][math]::Round($x0 + $ux * $i + $px * $w)
        $sy = [int][math]::Round($y0 + $uy * $i + $py * $w)
        if ($sx -lt 0 -or $sy -lt 0 -or $sx -ge $bmp.Width -or $sy -ge $bmp.Height) { continue }
        $c = $bmp.GetPixel($sx, $sy)
        $sum += [math]::Max($c.R, [math]::Max($c.G, $c.B)); $n++
    }
    $profile[$i] = if ($n -gt 0) { $sum / $n } else { -1 }
}
$bmp.Dispose()
$valid = @($profile | Where-Object { $_ -ge 0 })
if ($valid.Count -lt 20) { "only {0} samples of the axis fell inside the picture" -f $valid.Count; exit 1 }
$mean = ($valid | Measure-Object -Average).Average
$min = ($valid | Measure-Object -Minimum).Minimum
$max = ($valid | Measure-Object -Maximum).Maximum
# The local mean: a moving average over two and a half lug periods, wide enough to keep a lug and narrow enough to
# follow the rut's own shape. The profile minus it is what a lug shows up in.
$pxPerLug = $len / [math]::Max(1.0, $expected)
$win = [int][math]::Max(6, [math]::Round($pxPerLug * 2.5))
$flat = New-Object double[] ($steps + 1)
for ($i = 0; $i -le $steps; $i++) {
    if ($profile[$i] -lt 0) { $flat[$i] = -1000; continue }
    $a = [math]::Max(0, $i - [int]($win / 2)); $b = [math]::Min($steps, $i + [int]($win / 2))
    $s = 0.0; $n = 0
    for ($j = $a; $j -le $b; $j++) { if ($profile[$j] -ge 0) { $s += $profile[$j]; $n++ } }
    $flat[$i] = if ($n -gt 0) { $profile[$i] - $s / $n } else { -1000 }
}
$band = @($flat | Where-Object { $_ -gt -1000 })
$amp = ($band | ForEach-Object { [math]::Abs($_) } | Measure-Object -Average).Average
# Hysteresis of half the mean swing, so shader noise does not count as a lug.
$hyst = [math]::Max(0.5, $amp * 0.5)
$peaks = 0; $above = $false
foreach ($v in $band) {
    if (-not $above -and $v -gt $hyst) { $above = $true; $peaks++ }
    elseif ($above -and $v -lt -$hyst) { $above = $false }
}
$diff = [math]::Abs($peaks - $expected)
# The spacing itself, which does not care how many bright bands a lug shows the sun: the lag between half and twice the
# lug period at which the detrended profile correlates best with itself.
$var = 0.0; foreach ($v in $band) { $var += $v * $v }
$var = $var / [math]::Max(1, $band.Count)
$bestLag = 0; $bestR = -2.0
$loLag = [int][math]::Max(3, [math]::Round($pxPerLug * 0.5)); $hiLag = [int][math]::Round($pxPerLug * 2.0)
for ($lag = $loLag; $lag -le $hiLag; $lag++) {
    if ($lag -ge $band.Count - 8) { break }
    $s = 0.0; $n = 0
    for ($i = 0; $i -lt $band.Count - $lag; $i++) { $s += $band[$i] * $band[$i + $lag]; $n++ }
    $r = if ($n -gt 0 -and $var -gt 0) { ($s / $n) / $var } else { 0 }
    if ($r -gt $bestR) { $bestR = $r; $bestLag = $lag }
}
$byPeriod = if ($bestLag -gt 0) { $len / $bestLag } else { 0 }
"profile along the axis: {0} samples (half width {1} px), mean {2:N1}, min {3:N1}, max {4:N1}" -f $valid.Count, $HalfWidth, $mean, $min, $max
"about the local mean (window {0} px): mean swing {1:N1} levels, hysteresis {2:N1}" -f $win, $amp, $hyst
"peaks above the local mean: {0}   the field expects {1:N1}   difference {2:N1} (asked 2 or less)   px per lug {3:N1}" -f $peaks, $expected, $diff, $pxPerLug
"strongest repeat between {0} and {1} px: lag {2} px (correlation {3:N2}) = {4:N1} lugs along the axis, against {5:N1}" -f $loLag, $hiLag, $bestLag, $bestR, $byPeriod, $expected
# For reading that lag: the mud field's own 12.5 cm cell is this wide in the picture, and a cell edge is where one
# stamp's phase meets the next one's. A repeat at the cell and not at the lug means the phase jumped cell to cell.
"for scale: {0:N1} px per cm, so the field's 12.5 cm cell is {1:N1} px and a {2:N1} cm lug is {3:N1} px" -f ($len / $span), (12.5 * $len / $span), $lug, ($lug * $len / $span)

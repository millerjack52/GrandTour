# RIVERBED S3 (2026-09-23, VEHICLE_BUILD_SYSTEM 53): does the water stop at a straight line inside forda's pond? Reads
# Art/proving_shots.bat's step 2 picture (proving_04_forda_basin, the owner's picture 2: the pond from the forda
# station) and the runner's edge lines in Saved\Logs\proving_shots.log:
#   edge <picture> <upstream|downstream> <across m> wet x y dry x y | bed ... depth the car reads wet d dry d cm
# a pair of screen points on the water plane 1 m inside ("wet") and 1 m outside ("dry") the placed box's flow-wise end
# (the old straight edge), kept only where the bed under both stands under the level. Around each point a square of
# (2 x Half + 1) pixels; a pixel reads water when blue beats red (sample_ford.ps1's rule: water against the brown
# ground). Before S3 the dry side is ground (a step at the old edge); after it both sides should read water.
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_basin.ps1 [half]
param([int]$Half = 2)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root "Saved\Logs\proving_shots.log"
Add-Type -AssemblyName System.Drawing
if (-not (Test-Path $log)) { "no $log (run Art\proving_shots.bat 2)"; exit 1 }
$num = "([\d.\-]+)"
$lines = Select-String -Path $log -Pattern "edge (\S+) (upstream|downstream) $num wet $num $num dry $num $num \| .*depth the car reads wet $num dry $num cm"
if (-not $lines) { "no edge lines in $log"; exit 1 }
foreach ($hit in (Select-String -Path $log -Pattern "(GTWATERSTATS .*\(the picture's window\).*clamps (\d+), deficit ([\d.]+) s)")) {
    $g = $hit.Matches[0].Groups
    $s = $g[1].Value
    if ($s.Length -gt 230) { $s = $s.Substring(0, 230) + " ..." }
    "{0}{1}" -f $s, $(if ([int]$g[2].Value -ne 0) { "  *** clamped: the picture's water ran slow ***" } else { "" })
}
"water = blue over red, in a {0} x {0} px square round each point" -f (2 * $Half + 1)
$bitmaps = @{}
$stats = [ordered]@{}
foreach ($m in $lines) {
    $g = $m.Matches[0].Groups
    $pic = $g[1].Value; $end = $g[2].Value
    if (-not $bitmaps.ContainsKey($pic)) {
        $png = Join-Path $root ("Saved\Screenshots\Proving\" + $pic + ".png")
        if (Test-Path $png) { $bitmaps[$pic] = [System.Drawing.Bitmap]::FromFile($png) } else { "{0} missing picture" -f $pic; $bitmaps[$pic] = $null }
    }
    $bmp = $bitmaps[$pic]
    if (-not $bmp) { continue }
    $key = $pic + " " + $end
    if (-not $stats.Contains($key)) { $stats[$key] = @{ pairs = 0; wetPx = 0; wetBlue = 0; dryPx = 0; dryBlue = 0; wetDepth = 0.0; dryDepth = 0.0; wetR = 0.0; wetB = 0.0; dryR = 0.0; dryB = 0.0 } }
    $st = $stats[$key]
    $st.pairs++
    $st.wetDepth += [double]$g[8].Value; $st.dryDepth += [double]$g[9].Value
    foreach ($side in @(@("wet", [double]$g[4].Value, [double]$g[5].Value), @("dry", [double]$g[6].Value, [double]$g[7].Value))) {
        $cx = [int][math]::Round($side[1]); $cy = [int][math]::Round($side[2])
        for ($y = $cy - $Half; $y -le $cy + $Half; $y++) { for ($x = $cx - $Half; $x -le $cx + $Half; $x++) {
            if ($x -lt 0 -or $y -lt 0 -or $x -ge $bmp.Width -or $y -ge $bmp.Height) { continue }
            $c = $bmp.GetPixel($x, $y)
            $st[$side[0] + "Px"]++
            if ($c.B -gt $c.R) { $st[$side[0] + "Blue"]++ }
            $st[$side[0] + "R"] += $c.R; $st[$side[0] + "B"] += $c.B
        } }
    }
}
$all = @{ wetPx = 0; wetBlue = 0; dryPx = 0; dryBlue = 0; pairs = 0 }
foreach ($key in $stats.Keys) {
    $st = $stats[$key]
    $wp = [math]::Max(1, $st.wetPx); $dp = [math]::Max(1, $st.dryPx); $n = [math]::Max(1, $st.pairs)
    "{0,-40} {1,3} pairs: inside the old edge water {2:P1} (mean R {3:N0} B {4:N0}), outside it water {5:P1} (mean R {6:N0} B {7:N0}); the depth the car reads, mean inside {8:N1} cm, outside {9:N1} cm" -f `
        $key, $st.pairs, ($st.wetBlue / $wp), ($st.wetR / $wp), ($st.wetB / $wp), ($st.dryBlue / $dp), ($st.dryR / $dp), ($st.dryB / $dp), ($st.wetDepth / $n), ($st.dryDepth / $n)
    $all.wetPx += $st.wetPx; $all.wetBlue += $st.wetBlue; $all.dryPx += $st.dryPx; $all.dryBlue += $st.dryBlue; $all.pairs += $st.pairs
}
"{0,-40} {1,3} pairs: inside {2:P1}, outside {3:P1}, the step across the old edge {4:N1} points" -f "all", $all.pairs, ($all.wetBlue / [math]::Max(1, $all.wetPx)), ($all.dryBlue / [math]::Max(1, $all.dryPx)), (100.0 * ($all.wetBlue / [math]::Max(1, $all.wetPx) - $all.dryBlue / [math]::Max(1, $all.dryPx)))
foreach ($b in $bitmaps.Values) { if ($b) { $b.Dispose() } }

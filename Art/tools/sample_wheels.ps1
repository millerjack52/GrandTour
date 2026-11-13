# RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): how deep the tyres look in the ground in Art/proving_shots.bat's
# step 1 pictures (the car parked on forda's channel bank, proving_01_bank_left and proving_02_bank_right). For every
# wheel on the camera's side the runner logs a line in proving_shots.log:
#   wheel <picture> w<n> near 1 sunlit <0|1> occluder y box x0 y0 x1 y1 corners c low x y ground x y x y x y | ...
# a box round the drawn tyre's lower half, the drawn tyre's lowest point (the Chaos radius shrinks, the drawn tyre does
# not), the ground under the tyre's outer face half a radius behind, under and ahead of the hub, and the occluder (the
# highest the ground stands on screen over the 2 m between the face and the camera), all in pixels.
# The blockout's tyres are grey, not dark, so a "tyre pixel" is told from the ground by colour: the painterly Dirt is
# brown (red over blue by 35 or more), the tyre neutral. In each of the middle 40 % of the box's columns the sampler goes
# down from the box's top to the first row that starts three rows of ground; the row above it is the tyre's lowest
# visible pixel. It reports the median of those rows against the ground line at the same columns (interpolated between
# the three ground points) and against the occluder, in pixels: positive means the tyre ends above the line. Beside it
# the runner's own geometry: the drawn lowest point below the ground line. A picture from the shade side (sunlit 0) is
# reported but not measured: a grey tyre in the car's shade reads like the shadow on the ground around it.
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_wheels.ps1 [redOverBlue]
param([int]$Brown = 35)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root "Saved\Logs\proving_shots.log"
Add-Type -AssemblyName System.Drawing
$num = "([\d.\-]+)"
$pattern = "wheel (\S+) w(\d) near (\d) sunlit ([\d\-]+) occluder $num box $num $num $num $num corners (\d) low $num $num ground $num $num $num $num $num $num \| (.*)$"
$lines = Select-String -Path $log -Pattern $pattern
if (-not $lines) { "no wheel lines in $log"; exit 1 }
"ground pixel = red over blue by {0} or more (the Dirt is brown, the tyre grey); rows counted down from the top" -f $Brown
$bitmaps = @{}
foreach ($m in $lines) {
    $g = $m.Matches[0].Groups
    $pic = $g[1].Value; $w = $g[2].Value; $near = $g[3].Value; $sunlit = $g[4].Value; $occ = [double]$g[5].Value
    if ($near -ne "1") { continue }
    $png = Join-Path $root ("Saved\Screenshots\Proving\" + $pic + ".png")
    if (-not (Test-Path $png)) { "{0} w{1}: missing picture" -f $pic, $w; continue }
    if (-not $bitmaps.ContainsKey($pic)) { $bitmaps[$pic] = [System.Drawing.Bitmap]::FromFile($png) }
    $bmp = $bitmaps[$pic]
    $x0 = [double]$g[6].Value; $y0 = [double]$g[7].Value; $x1 = [double]$g[8].Value; $y1 = [double]$g[9].Value
    $lx = [double]$g[11].Value; $ly = [double]$g[12].Value
    $gx = @([double]$g[13].Value, [double]$g[15].Value, [double]$g[17].Value); $gy = @([double]$g[14].Value, [double]$g[16].Value, [double]$g[18].Value)
    $info = $g[19].Value
    function GroundAt([double]$x) {
        $pts = @(0, 1, 2) | Sort-Object { $gx[$_] }
        $a = $pts[0]; $b = $pts[1]; $c = $pts[2]
        if ($x -le $gx[$b]) { $p = $a; $q = $b } else { $p = $b; $q = $c }
        $dx = $gx[$q] - $gx[$p]
        if ([math]::Abs($dx) -lt 0.001) { return $gy[$p] }
        return $gy[$p] + ($gy[$q] - $gy[$p]) * ($x - $gx[$p]) / $dx
    }
    $bx0 = [math]::Max(0, [int][math]::Floor($x0)); $bx1 = [math]::Min($bmp.Width - 1, [int][math]::Ceiling($x1))
    $by0 = [math]::Max(0, [int][math]::Floor($y0)); $by1 = [math]::Min($bmp.Height - 1, [int][math]::Ceiling($y1))
    $half = [math]::Max(1, [int](0.2 * ($bx1 - $bx0)))
    $cx0 = [math]::Max($bx0, [int]$lx - $half); $cx1 = [math]::Min($bx1, [int]$lx + $half)
    $groundAtLow = GroundAt $lx
    $side = if ($sunlit -eq "1") { "sunlit" } elseif ($sunlit -eq "0") { "shade" } else { "sun unknown" }
    if ($sunlit -eq "0") {
        "{0} w{1} ({2}): not measured; the drawn lowest point {3:N1} px below the ground line, the occluder {4:N1} px above it" -f $pic, $w, $side, ($ly - $groundAtLow), ($groundAtLow - $occ)
        "    runner: {0}" -f $info
        continue
    }
    $diffs = @(); $rows = @()
    for ($x = $cx0; $x -le $cx1; $x++) {
        $isGround = @()
        for ($y = $by0; $y -le $by1; $y++) { $c = $bmp.GetPixel($x, $y); $isGround += (($c.R - $c.B) -ge $Brown) }
        $edge = -1
        for ($k = 0; $k -le $isGround.Count - 3; $k++) {
            if ($isGround[$k] -and $isGround[$k + 1] -and $isGround[$k + 2]) { $edge = $by0 + $k; break }
        }
        if ($edge -gt $by0) { $rows += ($edge - 1); $diffs += ((GroundAt $x) - ($edge - 1)) }
    }
    if ($diffs.Count -gt 0) {
        $sorted = $diffs | Sort-Object; $median = $sorted[[int][math]::Floor($sorted.Count / 2)]
        $sr = $rows | Sort-Object; $mrow = $sr[[int][math]::Floor($sr.Count / 2)]
        "{0} w{1} ({2}): the tyre's lowest visible pixel row {3} (median of {4} columns {5}..{6}); ground line at the face {7:N1}: {8:N1} px above it (columns {9:N1}..{10:N1}); occluder {11:N1}: {12:N1} px above it; the drawn lowest point {13:N1} px below the ground line" -f `
            $pic, $w, $side, $mrow, $diffs.Count, $cx0, $cx1, $groundAtLow, $median, $sorted[0], $sorted[-1], $occ, ($occ - $mrow), ($ly - $groundAtLow)
    } else {
        "{0} w{1} ({2}): no tyre-to-ground edge in columns {3}..{4}; the drawn lowest point {5:N1} px below the ground line" -f $pic, $w, $side, $cx0, $cx1, ($ly - $groundAtLow)
    }
    "    runner: {0}" -f $info
}
foreach ($b in $bitmaps.Values) { $b.Dispose() }

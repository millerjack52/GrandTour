# Counts the pixels of the ford's boxes (docs/WATER_PLAN.md stage W1, VEHICLE_BUILD_SYSTEM 39) in the three pictures
# hide_shots steps 22-24 take: hide_22_ford_bank (the crossing from the upstream bank, no car in the water),
# hide_23_ford_cross (the car crossing at 20 km/h, side on from the downstream bank) and hide_24_ford_deep (parked in
# it with the water raised 70 cm, from behind and to the right). Each box is a
#   "step NN: fordbox <picture> <box> x0 y0 x1 y1 corners on screen N"
# line of Saved\Logs\hide_shots.log, written by the runner from world points it projected: "water" the sheet's own
# surface, "bank" the far bank's waterline, "bow" the water just ahead of the car.
# Per box: how many pixels, their mean R/G/B, the share where blue beats red (water against tan ground), the count
# over 200 in the brightest channel (foam, spray and sky - near nothing in W1, the number W4 has to move) and the
# count under 40 (holes and shadow). This run is the baseline W4 is compared against; compare a ford run with a ford
# run only (the sun stands elsewhere in a full hide_shots run).
# The motion probe (the W1 follow-up, after the user drove it and saw no movement in the water): steps 25 and 26
# take two pictures 0.5 s apart from hide_22's eye with the flow and the wind running and two more with
# gt.Water.FlowScale 0 and gt.Water.Wind 0.
# The pairs section below counts, inside the water box, the share of pixels whose brightest channel moved by more
# than -DiffThreshold (12 of 255) between a and b. A tell that moves has to beat its own still pair: the gate is
# over 5 % flowing and under 1 % still.
# Water stage WS2 adds a third pair, hide_27_ford_wake_a and _b, a second apart from hide_23's eye after the car has
# crossed: the wake it left behind has to move more than 5 % of that box, and step 28's hide_28_ford_rain puts the
# rain's rings on the same line hide_22 counts its crests along.
# Water stage W4 (the look: the depth tint, the sourced ripple normal carried by the flow, the foam) adds step 29's
# hide_29_ford_shallow, taken from the near bank at eye height looking down at the water where the bed still shows
# through it, with two boxes - "edge" the first two metres in (a few cm of water: the foam's shallow term) and
# "shallow" three to eight metres in. Nothing below needed changing for it: the box and line sections walk every
# fordbox and fordline line in the log. What the user judges there is the mean R/G/B of each box and its bright
# count; the runner logs the depths the field reads in the same two places beside the picture.
# The ring (water stage WS1): hide_22 is now taken 1.5 s after the runner drops a 20 cm impulse over a 1 m disc
# at the sheet's middle, and the runner logs a line across the water along the flow as
#   "step 22: fordline <picture> <name> x0 y0 x1 y1 ends on screen N".
# The crests section at the end walks that line in the picture, averaging a few pixels across it, and counts the
# brightness maxima that rise over the line's own mean + CrestThreshold. A flat sheet has none.
# Water stage R1 adds two things: every picture is printed with the GTWATERSTATS line of the step it was taken in
# (frame ms, the field's step ms, sub-steps asked against run, the clamp count and the simulated time it cost), and a
# picture whose step clamped is marked VOID - the water ran slow for part of that step, so its picture is not
# comparable with one from a run that kept up. R1 also adds step 30's hide_31_ford_rock, the eye on the near bank at a
# rock that stands over the surface, with two boxes: "rock" the ring round its waterline (W4's foam rings anything in
# under 12 cm of water) and "open" the same ring of open water three metres to the side. Nothing below needed changing
# for it: the box section walks every fordbox line in the log.
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_ford.ps1 [diffThreshold] [crestThreshold]
param([int]$DiffThreshold = 12, [int]$CrestThreshold = 8)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root "Saved\Logs\hide_shots.log"
Add-Type -AssemblyName System.Drawing
if (-not (Test-Path $log)) { "no $log (run Art\ford_shots.bat)"; exit 1 }

$lines = Select-String -Path $log -Pattern "fordbox (\S+) (\S+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d+)"
if (-not $lines) { "no fordbox lines in $log"; exit 1 }

# The last line for each picture+box pair wins (a re-run appends to the same log).
$boxes = [ordered]@{}
foreach ($line in $lines) {
    $g = $line.Matches[0].Groups
    $boxes[($g[1].Value + " " + $g[2].Value)] = $g
}

# ---- water stage R1: what the water cost during the step each picture was taken in ----
# The runner logs a GTWATERSTATS line at the end of every step (AGTWaterSheet's step window). A picture taken in a
# step whose clamp count is not 0 was taken while the solver could not keep up with the frame time - the water ran in
# slow motion for part of it - and the picture is VOID: it is not comparable with a run that did not clamp.
$stepStats = @{}
foreach ($hit in (Select-String -Path $log -Pattern "step (\d+): (GTWATERSTATS .*clamps (\d+), deficit ([\d.]+) s)")) {
    $g = $hit.Matches[0].Groups
    $stepStats[[int]$g[1].Value] = @{ line = $g[2].Value; clamps = [int]$g[3].Value; deficit = [double]$g[4].Value }
}
$pictureStep = @{}
foreach ($hit in (Select-String -Path $log -Pattern "step (\d+): fordbox (\S+) ")) {
    $g = $hit.Matches[0].Groups
    $pictureStep[$g[2].Value] = [int]$g[1].Value
}

"water = blue over red; bright = the brightest channel over 200 (foam, spray, sky); dark = under 40"
$lastPicture = ""
$bmp = $null
foreach ($key in $boxes.Keys) {
    $g = $boxes[$key]
    $picture = $g[1].Value
    $box = $g[2].Value
    if ($picture -ne $lastPicture) {
        if ($bmp) { $bmp.Dispose(); $bmp = $null }
        $png = Join-Path $root ("Saved\Screenshots\M6\" + $picture + ".png")
        if (Test-Path $png) { $bmp = [System.Drawing.Bitmap]::FromFile($png) } else { "{0,-20} missing picture" -f $picture }
        $lastPicture = $picture
        # R1: the water's own cost in the step this picture was taken in, and whether that voids it.
        $st = $null
        $step = -1
        if ($pictureStep.ContainsKey($picture)) { $step = $pictureStep[$picture]; if ($stepStats.ContainsKey($step)) { $st = $stepStats[$step] } }
        if ($st) {
            if ($st.clamps -ne 0) {
                "{0,-20} step {1}: {2}" -f $picture, $step, $st.line
                "{0,-20} *** VOID: the water lost {1:N3} s of simulated time in {2} clamped frame(s) of this step ***" -f "", $st.deficit, $st.clamps
            } else {
                "{0,-20} step {1}: {2}" -f $picture, $step, $st.line
            }
        } else {
            "{0,-20} no GTWATERSTATS line for its step (an old log, or the picture was taken outside a water step)" -f $picture
        }
    }
    if (-not $bmp) { continue }
    $x0 = [math]::Max(0, [int][math]::Floor([double]$g[3].Value)); $y0 = [math]::Max(0, [int][math]::Floor([double]$g[4].Value))
    $x1 = [math]::Min($bmp.Width - 1, [int][math]::Ceiling([double]$g[5].Value)); $y1 = [math]::Min($bmp.Height - 1, [int][math]::Ceiling([double]$g[6].Value))
    $n = 0; $sr = 0.0; $sg = 0.0; $sb = 0.0; $blue = 0; $bright = 0; $dark = 0
    for ($y = $y0; $y -le $y1; $y++) { for ($x = $x0; $x -le $x1; $x++) {
        $c = $bmp.GetPixel($x, $y); $n++
        $sr += $c.R; $sg += $c.G; $sb += $c.B
        if ($c.B -gt $c.R) { $blue++ }
        $top = [math]::Max($c.R, [math]::Max($c.G, $c.B))
        if ($top -gt 200) { $bright++ }
        if ($top -lt 40) { $dark++ }
    } }
    $d = [math]::Max(1, $n)
    "{0,-20} {1,-6} {2}x{3} box {4},{5}-{6},{7} (corners on screen {8}): {9} px, mean {10:N0} {11:N0} {12:N0}, water {13:P1}, bright {14} ({15:P2}), dark {16} ({17:P2})" -f `
        $picture, $box, $bmp.Width, $bmp.Height, $x0, $y0, $x1, $y1, $g[7].Value, $n, ($sr / $d), ($sg / $d), ($sb / $d), ($blue / $d), $bright, ($bright / $d), $dark, ($dark / $d)
}
if ($bmp) { $bmp.Dispose() }

# ---- the motion probe: how much of the water box changed between the two frames of each pair ----
""
"frame-diff over the water box: the share of pixels whose brightest channel moved by more than {0} between a and b" -f $DiffThreshold
foreach ($pair in @(@("hide_25_ford_flow_a", "hide_25_ford_flow_b", "flow+wind on"), @("hide_26_ford_still_a", "hide_26_ford_still_b", "flow+wind off"), @("hide_27_ford_wake_a", "hide_27_ford_wake_b", "wake 1 s apart"))) {
    $key = $pair[0] + " water"
    if (-not $boxes.Contains($key)) { "{0,-20} no fordbox line for {1}" -f $pair[2], $pair[0]; continue }
    $g = $boxes[$key]
    $pa = Join-Path $root ("Saved\Screenshots\M6\" + $pair[0] + ".png")
    $pb = Join-Path $root ("Saved\Screenshots\M6\" + $pair[1] + ".png")
    if (-not (Test-Path $pa) -or -not (Test-Path $pb)) { "{0,-20} missing picture" -f $pair[2]; continue }
    $ba = [System.Drawing.Bitmap]::FromFile($pa)
    $bb = [System.Drawing.Bitmap]::FromFile($pb)
    $x0 = [math]::Max(0, [int][math]::Floor([double]$g[3].Value)); $y0 = [math]::Max(0, [int][math]::Floor([double]$g[4].Value))
    $x1 = [math]::Min([math]::Min($ba.Width, $bb.Width) - 1, [int][math]::Ceiling([double]$g[5].Value))
    $y1 = [math]::Min([math]::Min($ba.Height, $bb.Height) - 1, [int][math]::Ceiling([double]$g[6].Value))
    $n = 0; $moved = 0; $sum = 0.0; $peak = 0
    for ($y = $y0; $y -le $y1; $y++) { for ($x = $x0; $x -le $x1; $x++) {
        $ca = $ba.GetPixel($x, $y); $cb = $bb.GetPixel($x, $y); $n++
        $ta = [math]::Max($ca.R, [math]::Max($ca.G, $ca.B)); $tb = [math]::Max($cb.R, [math]::Max($cb.G, $cb.B))
        $d = [math]::Abs($ta - $tb); $sum += $d
        if ($d -gt $peak) { $peak = $d }
        if ($d -gt $DiffThreshold) { $moved++ }
    } }
    $d0 = [math]::Max(1, $n)
    "{0,-20} {1} px of the water box: moved {2} ({3:P2}), mean change {4:N2}, biggest {5}" -f `
        $pair[2], $n, $moved, ($moved / $d0), ($sum / $d0), $peak
    $ba.Dispose(); $bb.Dispose()
}

# ---- the ring: brightness maxima along the logged line across the water (water stage WS1) ----
""
"crests along the fordline: maxima rising over the line's mean + {0}" -f $CrestThreshold
$lineHits = Select-String -Path $log -Pattern "fordline (\S+) (\S+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ends on screen (\d+)"
if (-not $lineHits) { "no fordline lines in $log" }
else {
    $lines = [ordered]@{}
    foreach ($hit in $lineHits) { $g = $hit.Matches[0].Groups; $lines[($g[1].Value + " " + $g[2].Value)] = $g }
    foreach ($key in $lines.Keys) {
        $g = $lines[$key]
        $picture = $g[1].Value
        $name = $g[2].Value
        $png = Join-Path $root ("Saved\Screenshots\M6\" + $picture + ".png")
        if (-not (Test-Path $png)) { "{0,-20} {1,-6} missing picture" -f $picture, $name; continue }
        $img = [System.Drawing.Bitmap]::FromFile($png)
        $x0 = [double]$g[3].Value; $y0 = [double]$g[4].Value; $x1 = [double]$g[5].Value; $y1 = [double]$g[6].Value
        $dx = $x1 - $x0; $dy = $y1 - $y0
        $len = [math]::Sqrt($dx * $dx + $dy * $dy)
        if ($len -lt 20) { "{0,-20} {1,-6} the line is only {2:N0} px long" -f $picture, $name, $len; $img.Dispose(); continue }
        $ux = $dx / $len; $uy = $dy / $len
        $px = -$uy; $py = $ux
        $steps = [int][math]::Floor($len)
        $profile = New-Object double[] ($steps + 1)
        $used = 0
        for ($i = 0; $i -le $steps; $i++) {
            $sum = 0.0; $n = 0
            for ($w = -2; $w -le 2; $w++) {
                $sx = [int][math]::Round($x0 + $ux * $i + $px * $w)
                $sy = [int][math]::Round($y0 + $uy * $i + $py * $w)
                if ($sx -lt 0 -or $sy -lt 0 -or $sx -ge $img.Width -or $sy -ge $img.Height) { continue }
                $c = $img.GetPixel($sx, $sy)
                $sum += [math]::Max($c.R, [math]::Max($c.G, $c.B)); $n++
            }
            if ($n -gt 0) { $profile[$i] = $sum / $n; $used++ } else { $profile[$i] = -1 }
        }
        $img.Dispose()
        $valid = @($profile | Where-Object { $_ -ge 0 })
        if ($valid.Count -lt 20) { "{0,-20} {1,-6} only {2} sampled pixels on screen" -f $picture, $name, $valid.Count; continue }
        $mean = ($valid | Measure-Object -Average).Average
        $sd = [math]::Sqrt((($valid | ForEach-Object { ($_ - $mean) * ($_ - $mean) } | Measure-Object -Sum).Sum) / $valid.Count)
        $hi = $mean + $CrestThreshold
        $lo = $mean + $CrestThreshold * 0.5
        $crests = 0; $above = $false
        foreach ($v in $profile) {
            if ($v -lt 0) { continue }
            if (-not $above -and $v -gt $hi) { $above = $true; $crests++ }
            elseif ($above -and $v -lt $lo) { $above = $false }
        }
        "{0,-20} {1,-6} {2:N0} px of line ({3} on screen), mean {4:N1}, sd {5:N1}: {6} crests over {7:N1}" -f `
            $picture, $name, $len, $g[7].Value, $mean, $sd, $crests, $hi
    }
}

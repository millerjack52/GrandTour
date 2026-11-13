# Counts the dark and the sky-coloured pixels along the mud patch box's border (mud plan stage D, section 31) in the two
# pictures hide_shots step 14 takes of it: hide_17_border_low (eye height, 3 m outside the box, 19 degrees down) and
# hide_18_border_far (the same bearing from 40 m, the landscape's LOD crack check). Each picture's box is the
# "step 14: borderbox <name> x0 y0 x1 y1" line of hide_shots.log: the border's two ends, 60 cm either side, projected.
# A pixel is dark when its brightest channel is under the threshold (a lit mud or ground surface reads well over 100; a
# hole in both surfaces reads under 30) and sky-coloured when blue is its brightest channel by at least 15 (the sky
# through a crack read 21 29 39 in section 30; mud and dirt are tan, R > G > B). Expect 0 of both in both pictures.
# Then, from the low picture, the mean brightest channel of 3 x 1 m of mud mesh 1.5 m inside the box (mudstrip) against
# the same of landscape 1.5 m outside it (landstrip) and the difference: the mesh has no MF_Weather puddles, so the two
# can part (stage D reports it, stage E's textures are meant to close it).
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_border.ps1 [threshold]
# RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): the same count on another run's picture - L_Proving's ford bed patch edge:
#   ... sample_border.ps1 -LogName proving_shots.log -Folder Proving -Step 3 -Names proving_07_forda_box_edge
# (the mud/land strips are read from the first picture named).
param([int]$Threshold = 40, [string]$LogName = "hide_shots.log", [string]$Folder = "M6", [int]$Step = 14, [string[]]$Names = @("hide_17_border_low", "hide_18_border_far"))
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root ("Saved\Logs\" + $LogName)
Add-Type -AssemblyName System.Drawing

function Get-Box($name) {
    $m = Select-String -Path $log -Pattern ("step " + $Step + ": borderbox " + $name + " ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) corners on screen (\d)") | Select-Object -Last 1
    if (-not $m) { return $null }
    return $m.Matches[0].Groups
}

function Measure-Region($bmp, $g, $threshold) {
    $x0 = [math]::Max(0, [int][math]::Floor([double]$g[1].Value)); $y0 = [math]::Max(0, [int][math]::Floor([double]$g[2].Value))
    $x1 = [math]::Min($bmp.Width - 1, [int][math]::Ceiling([double]$g[3].Value)); $y1 = [math]::Min($bmp.Height - 1, [int][math]::Ceiling([double]$g[4].Value))
    $dark = 0; $sky = 0; $n = 0; $sum = 0.0; $dr = 0; $dg = 0; $db = 0; $bins = @(0, 0, 0, 0, 0, 0)
    for ($y = $y0; $y -le $y1; $y++) { for ($x = $x0; $x -le $x1; $x++) {
        $c = $bmp.GetPixel($x, $y); $b = [math]::Max($c.R, [math]::Max($c.G, $c.B)); $n++; $sum += $b
        if ($b -lt $threshold) { $dark++; $dr += $c.R; $dg += $c.G; $db += $c.B }
        if ($c.B -gt $c.R -and $c.B -gt $c.G -and ($c.B - $c.R) -ge 15) { $sky++ }
        if ($b -lt 40) { $bins[0]++ } elseif ($b -lt 100) { $bins[1]++ } elseif ($b -lt 160) { $bins[2]++ } elseif ($b -lt 200) { $bins[3]++ } elseif ($b -lt 235) { $bins[4]++ } else { $bins[5]++ }
    } }
    return [pscustomobject]@{ X0 = $x0; Y0 = $y0; X1 = $x1; Y1 = $y1; N = $n; Dark = $dark; Sky = $sky; Mean = ($sum / [math]::Max(1, $n));
        DR = ($dr / [math]::Max(1, $dark)); DG = ($dg / [math]::Max(1, $dark)); DB = ($db / [math]::Max(1, $dark)); Bins = $bins }
}

"dark = brightest channel under {0}; sky = blue the brightest channel by 15 or more" -f $Threshold
foreach ($name in $Names) {
    $g = Get-Box $name
    if (-not $g) { "{0,-20} no borderbox line in $log" -f $name; continue }
    $png = Join-Path $root ("Saved\Screenshots\" + $Folder + "\" + $name + ".png")
    if (-not (Test-Path $png)) { "{0,-20} missing picture" -f $name; continue }
    $bmp = [System.Drawing.Bitmap]::FromFile($png)
    $r = Measure-Region $bmp $g $Threshold
    "{0,-20} {1}x{2} borderbox {3},{4}-{5},{6} (corners on screen {13}): dark {7} of {8} ({9:P1}), sky {10} ({11:P1}), mean brightest channel {12:N1}" -f `
        $name, $bmp.Width, $bmp.Height, $r.X0, $r.Y0, $r.X1, $r.Y1, $r.Dark, $r.N, ($r.Dark / [math]::Max(1, $r.N)), $r.Sky, ($r.Sky / [math]::Max(1, $r.N)), $r.Mean, $g[5].Value
    "{0,-20} brightest channel <40: {1}  40-100: {2}  100-160: {3}  160-200: {4}  200-235: {5}  >=235: {6}; mean colour of the dark pixels {7:N0} {8:N0} {9:N0}" -f `
        "", $r.Bins[0], $r.Bins[1], $r.Bins[2], $r.Bins[3], $r.Bins[4], $r.Bins[5], $r.DR, $r.DG, $r.DB
    if ($name -eq $Names[0]) {
        $means = @{}
        foreach ($strip in @("mudstrip", "landstrip")) {
            $sg = Get-Box $strip
            if (-not $sg) { "{0,-20} no {1} line" -f "", $strip; continue }
            $sr = Measure-Region $bmp $sg $Threshold
            $means[$strip] = $sr.Mean
            "{0,-20} {1,-9} {2},{3}-{4},{5}: {6} px, mean brightest channel {7:N1}" -f "", $strip, $sr.X0, $sr.Y0, $sr.X1, $sr.Y1, $sr.N, $sr.Mean
        }
        if ($means.ContainsKey("mudstrip") -and $means.ContainsKey("landstrip")) {
            "{0,-20} mud inside the box minus landscape outside it: {1:N1}" -f "", ($means["mudstrip"] - $means["landstrip"])
        }
    }
    $bmp.Dispose()
}

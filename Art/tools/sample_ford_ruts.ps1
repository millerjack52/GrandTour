# RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): the ruts under forda's water on L_Proving, from Art\proving_shots.bat 3.
# The runner logs, for the one camera both pictures share (proving_05_forda_ruts_before, proving_06_forda_ruts_after),
# the left wheels' path over the first metres of the water as "rutpt rut x y r field f" (a disc of r pixels round each
# point: 12 cm either side of the tyre's path at the mud's surface) and the same path 2.5 m further left, over untouched
# wet bed, as "rutpt ctrl ...". Per picture and per set: the pixels, the mean brightest channel, the share under the
# dark threshold and the mean colour; then, pixel by pixel, how many changed between the two pictures by more than the
# change threshold (the ruts are the only thing that should differ; the control's share is the noise: auto exposure,
# the water's own shimmer). This is the sample_rut_low.ps1 pattern on a before/after pair.
#   powershell -ExecutionPolicy Bypass -File Art\tools\sample_ford_ruts.ps1 [dark] [change]
param([int]$Threshold = 40, [int]$Change = 12)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $root "Saved\Logs\proving_shots.log"
Add-Type -AssemblyName System.Drawing

$sets = @{ rut = @{}; ctrl = @{} }
$fields = @{ rut = @(); ctrl = @() }
foreach ($m in (Select-String -Path $log -Pattern "rutpt (rut|ctrl) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) field ([\d.\-]+)")) {
    $g = $m.Matches[0].Groups
    $kind = $g[1].Value; $cx = [double]$g[2].Value; $cy = [double]$g[3].Value; $r = [double]$g[4].Value
    $fields[$kind] += [double]$g[5].Value
    $ri = [int][math]::Ceiling($r)
    for ($dy = -$ri; $dy -le $ri; $dy++) { for ($dx = -$ri; $dx -le $ri; $dx++) {
        if ($dx * $dx + $dy * $dy -gt $r * $r) { continue }
        $x = [int][math]::Round($cx + $dx); $y = [int][math]::Round($cy + $dy)
        $sets[$kind]["$x,$y"] = @($x, $y)
    } }
}
if ($sets.rut.Count -eq 0) { "no rutpt lines in $log"; exit 1 }
foreach ($kind in @("rut", "ctrl")) {
    $f = $fields[$kind]
    "{0,-4} {1} points, the field under them mean {2:N2} cm (min {3:N2}), {4} pixels" -f $kind, $f.Count, (($f | Measure-Object -Average).Average), (($f | Measure-Object -Minimum).Minimum), $sets[$kind].Count
}
$bmps = @{}
foreach ($pic in @("proving_05_forda_ruts_before", "proving_06_forda_ruts_after")) {
    $png = Join-Path $root ("Saved\Screenshots\Proving\" + $pic + ".png")
    if (-not (Test-Path $png)) { "$pic missing"; exit 1 }
    $bmps[$pic] = [System.Drawing.Bitmap]::FromFile($png)
}
$bright = @{}
foreach ($pic in $bmps.Keys | Sort-Object) {
    $bmp = $bmps[$pic]
    foreach ($kind in @("rut", "ctrl")) {
        $n = 0; $sum = 0.0; $dark = 0; $sr = 0.0; $sg = 0.0; $sb = 0.0
        $vals = @{}
        foreach ($p in $sets[$kind].Values) {
            if ($p[0] -lt 0 -or $p[1] -lt 0 -or $p[0] -ge $bmp.Width -or $p[1] -ge $bmp.Height) { continue }
            $c = $bmp.GetPixel($p[0], $p[1]); $b = [math]::Max($c.R, [math]::Max($c.G, $c.B))
            $n++; $sum += $b; $sr += $c.R; $sg += $c.G; $sb += $c.B
            if ($b -lt $Threshold) { $dark++ }
            $vals["$($p[0]),$($p[1])"] = $b
        }
        $bright["$pic|$kind"] = $vals
        $d = [math]::Max(1, $n)
        "{0,-30} {1,-4} {2} px: mean brightest channel {3:N1}, dark (<{4}) {5:P1}, mean RGB {6:N0} {7:N0} {8:N0}" -f $pic, $kind, $n, ($sum / $d), $Threshold, ($dark / $d), ($sr / $d), ($sg / $d), ($sb / $d)
    }
}
foreach ($kind in @("rut", "ctrl")) {
    $a = $bright["proving_05_forda_ruts_before|$kind"]; $b = $bright["proving_06_forda_ruts_after|$kind"]
    $n = 0; $changed = 0; $sumd = 0.0; $absd = 0.0
    foreach ($k in $a.Keys) {
        if (-not $b.ContainsKey($k)) { continue }
        $diff = $b[$k] - $a[$k]; $n++; $sumd += $diff; $absd += [math]::Abs($diff)
        if ([math]::Abs($diff) -gt $Change) { $changed++ }
    }
    $d = [math]::Max(1, $n)
    "{0,-4} after minus before: {1} px, mean {2:N1}, mean |diff| {3:N1}, changed by more than {4}: {5} ({6:P1})" -f $kind, $n, ($sumd / $d), ($absd / $d), $Change, $changed, ($changed / $d)
}
foreach ($bmp in $bmps.Values) { $bmp.Dispose() }

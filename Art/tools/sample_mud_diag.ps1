# Samples Saved/Screenshots/M6/hide_12_mud_diag.png at the pixels the hide shots logged ("diag <name> px x y ...")
# and prints name, pixel, RGB and the field/ground numbers the runner logged, so the mud picture is judged by
# numbers: red = the mud height (0.5 flat, lower in a rut, higher on a ridge), green = the ground's Z over the
# patch, blue = the tracks.   powershell -ExecutionPolicy Bypass -File Art\tools\sample_mud_diag.ps1
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$png = Join-Path $root "Saved\Screenshots\M6\hide_12_mud_diag.png"
$log = Join-Path $root "Saved\Logs\hide_shots.log"
Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Bitmap]::FromFile($png)
"image {0}x{1}" -f $bmp.Width, $bmp.Height
$lines = Select-String -Path $log -Pattern "step 12: diag (\S+) px ([\d.\-]+) ([\d.\-]+) on (\d) world (\S+) (\S+) rest (\S+) field (\S+) tracks (\S+)"
foreach ($m in $lines) {
    $g = $m.Matches[0].Groups
    $x = [int][math]::Round([double]$g[2].Value)
    $y = [int][math]::Round([double]$g[3].Value)
    if ($x -lt 0 -or $y -lt 0 -or $x -ge $bmp.Width -or $y -ge $bmp.Height) { "{0,-12} px {1},{2} OFF IMAGE" -f $g[1].Value, $x, $y; continue }
    # a 3x3 mean so a one-pixel rounding does not decide it
    $r = 0; $gg = 0; $b = 0; $n = 0
    for ($dy = -1; $dy -le 1; $dy++) { for ($dx = -1; $dx -le 1; $dx++) {
        $xx = $x + $dx; $yy = $y + $dy
        if ($xx -ge 0 -and $yy -ge 0 -and $xx -lt $bmp.Width -and $yy -lt $bmp.Height) { $c = $bmp.GetPixel($xx, $yy); $r += $c.R; $gg += $c.G; $b += $c.B; $n++ }
    } }
    "{0,-12} px {1,4},{2,4}  R {3,5:N1} G {4,5:N1} B {5,5:N1}   rest {6,7} field {7,6} tracks {8}" -f $g[1].Value, $x, $y, ($r / $n), ($gg / $n), ($b / $n), $g[7].Value, $g[8].Value, $g[9].Value
}
$bmp.Dispose()

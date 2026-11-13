# Stage B step 2 (docs/LandscapeMigrationManifest.md 9.B.2): byte copy of the audited closure.
# Copies every file of each package in docs/landscape_migration/copy_set.txt from the source project's
# Content to GrandTour's Content (identical /Game paths), plus the STYLIZED_COZY_TREES licence file.
# The source is only read. Content is not under git, so this script REFUSES to run if any destination
# file already exists (checked for the whole set before anything is copied).
#   powershell -ExecutionPolicy Bypass -File Art\dressing\copy_closure.ps1 -DryRun   (lists, copies nothing)
#   powershell -ExecutionPolicy Bypass -File Art\dressing\copy_closure.ps1           (copies + SHA-1 check)
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$SrcRoot = 'D:\Dev\OWGameUE\Content'
$DstRoot = 'C:\GrandTour\Content'
$SetFile = 'C:\GrandTour\docs\landscape_migration\copy_set.txt'
$LogFile = 'C:\GrandTour\docs\landscape_migration\copied_files.txt'
$Exts = @('.uasset', '.umap', '.uexp', '.ubulk', '.uptnl')
$ExtraFiles = @('3DAssets\STYLIZED_COZY_TREES_LICENSE.txt')

# ---- build the file list
$pkgs = @(Get-Content -LiteralPath $SetFile | Where-Object { $_ -and -not $_.StartsWith('#') } |
          ForEach-Object { ($_ -split "`t")[0] })
$items = New-Object System.Collections.Generic.List[object]
$noMain = @()
foreach ($p in $pkgs) {
    if (-not $p.StartsWith('/Game/')) { throw "not a /Game package: $p" }
    $rel = $p.Substring(6).Replace('/', '\')
    $hasMain = $false
    foreach ($e in $Exts) {
        $s = Join-Path $SrcRoot ($rel + $e)
        if (Test-Path -LiteralPath $s -PathType Leaf) {
            $items.Add([pscustomobject]@{ Package = $p; Rel = $rel + $e; Src = $s; Dst = (Join-Path $DstRoot ($rel + $e)) })
            if ($e -eq '.uasset' -or $e -eq '.umap') { $hasMain = $true }
        }
    }
    if (-not $hasMain) { $noMain += $p }
}
foreach ($x in $ExtraFiles) {
    $s = Join-Path $SrcRoot $x
    if (-not (Test-Path -LiteralPath $s -PathType Leaf)) { throw "extra file missing in source: $s" }
    $items.Add([pscustomobject]@{ Package = '(file)'; Rel = $x; Src = $s; Dst = (Join-Path $DstRoot $x) })
}
if ($noMain.Count -gt 0) {
    Write-Output ("ABORT: {0} packages have no .uasset/.umap in the source:" -f $noMain.Count)
    $noMain | ForEach-Object { Write-Output "  $_" }
    exit 3
}

# ---- refuse to overwrite anything
$existing = @($items | Where-Object { Test-Path -LiteralPath $_.Dst })
$srcBytes = [int64]0
foreach ($it in $items) { $srcBytes += (Get-Item -LiteralPath $it.Src).Length }
Write-Output ("packages {0}, files {1}, source bytes {2}, destinations already present {3}" -f `
    $pkgs.Count, $items.Count, $srcBytes, $existing.Count)
if ($existing.Count -gt 0) {
    Write-Output 'ABORT: these destination files already exist (nothing copied):'
    $existing | ForEach-Object { Write-Output ('  ' + $_.Dst) }
    exit 2
}
if ($DryRun) { Write-Output 'DRY RUN: no destination exists; nothing copied.'; exit 0 }

# ---- copy, then hash both sides
$sha = [System.Security.Cryptography.SHA1]::Create()
function Get-Sha1([string]$path) {
    $fs = [System.IO.File]::OpenRead($path)
    try { return ([System.BitConverter]::ToString($sha.ComputeHash($fs))).Replace('-', '') } finally { $fs.Dispose() }
}
$rows = New-Object System.Collections.Generic.List[string]
$match = 0; $copiedBytes = [int64]0
foreach ($it in $items) {
    $dir = Split-Path -Parent $it.Dst
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item -LiteralPath $it.Src -Destination $it.Dst
    $len = (Get-Item -LiteralPath $it.Dst).Length
    $copiedBytes += $len
    $hs = Get-Sha1 $it.Src
    $hd = Get-Sha1 $it.Dst
    $ok = ($hs -eq $hd)
    if ($ok) { $match++ }
    $rows.Add(("{0}`t{1}`t{2}`t{3}" -f $it.Rel, $len, $hd, $(if ($ok) { 'match' } else { "MISMATCH src=$hs" })))
}
$hdr = @(
    '# Stage B copy log (docs/LandscapeMigrationManifest.md 9.B.2), written by Art/dressing/copy_closure.ps1',
    ('# {0}  source {1} -> target {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $SrcRoot, $DstRoot),
    ('# packages {0}; files {1}; bytes {2}; SHA-1 match {3}/{1}' -f $pkgs.Count, $items.Count, $copiedBytes, $match),
    '# <path under Content>\t<bytes>\t<sha1>\t<match>'
)
[System.IO.File]::WriteAllLines($LogFile, [string[]]($hdr + $rows))
Write-Output ('copied files {0}, bytes {1}, SHA-1 match {2}/{0}; log {3}' -f $items.Count, $copiedBytes, $match, $LogFile)
if ($match -ne $items.Count) { exit 1 }
exit 0

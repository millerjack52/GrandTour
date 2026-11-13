param([Parameter(Mandatory=$true)][string]$Report)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$file=(Resolve-Path -LiteralPath $Report).Path
$evidenceRoot=(Resolve-Path -LiteralPath (Join-Path $root 'Art/Export/BenmoreGaea')).Path
if(-not $file.StartsWith($evidenceRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Expected a Benmore LOD trial report'}
$data=Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
$rows=@($data.assets | Where-Object {$_.saved})
if(-not $rows.Count){throw 'No recorded mesh saves to restore'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
if(-not $mutex.WaitOne(0)){$mutex.Dispose();throw 'Unreal slot reserved'}
try {
    if(@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealInsights|MSBuild|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }).Count){throw 'Close/finish Unreal and build work before package restoration'}
    # Validate every target and backup before restoring the first package.
    $meshRoot=(Resolve-Path -LiteralPath (Join-Path $root 'Content/GrandTour/Vehicles/FleetDriving')).Path
    foreach($row in $rows){
        $target=(Resolve-Path -LiteralPath $row.file).Path
        $backup=(Resolve-Path -LiteralPath $row.backup).Path
        if(-not $target.StartsWith($meshRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($target) -ne '.uasset'){throw 'Unexpected mesh package target'}
        if(-not $backup.StartsWith((Split-Path $file)+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Backup outside the recorded trial'}
        if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $row.after_sha256){throw ('Later package edit detected; will not overwrite '+$target)}
        if((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ne $row.before_sha256){throw 'Backup hash mismatch'}
    }
    foreach($row in $rows){
        Copy-Item -LiteralPath $row.backup -Destination $row.file
        if((Get-FileHash -LiteralPath $row.file -Algorithm SHA256).Hash -ne $row.before_sha256){throw 'Restored package hash mismatch'}
    }
    Write-Output ('Restored '+$rows.Count+' trial meshes to their recorded original packages')
} finally {$mutex.ReleaseMutex();$mutex.Dispose()}

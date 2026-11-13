param([Parameter(Mandatory)][string]$EvidenceRun,
      [Parameter(Mandatory)][switch]$ImagesReviewed)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if($EvidenceRun -notmatch '^\d{8}T\d{9}Z-[a-f0-9]{8}$'){throw 'Expected a recorded performance run ID'}
if(-not $ImagesReviewed){throw 'Inspect reference and candidate images first'}
$evidence=Join-Path $root "Art/Export/BenmoreGaea/PerformanceRuns/$EvidenceRun"
if(-not (Test-Path -LiteralPath (Join-Path $evidence 'profile-report.json'))){throw 'Missing evidence'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
if(-not $mutex.WaitOne(0)){$mutex.Dispose();throw 'Another guarded operation owns the slot'}
$oldEvidence=$env:GT_BENMORE_NANITE_EVIDENCE
$oldOutput=$env:GT_BENMORE_NANITE_INSTALL_OUT
$oldReview=$env:GT_BENMORE_NANITE_VISUAL_REVIEW
try {
    $deadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^(UnrealEditor.*|GrandTour.*|MSBuild|ShaderCompileWorker|cl|link)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $busy.Count){break}
        if([DateTime]::UtcNow -ge $deadline){throw 'Slot remained occupied; nothing closed or launched'}
        Start-Sleep -Seconds 5
    } while($true)
    $stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
    $out=Join-Path $root "Art/Export/BenmoreGaea/NaniteInstall_$stamp"
    $env:GT_BENMORE_NANITE_EVIDENCE=$evidence
    $env:GT_BENMORE_NANITE_INSTALL_OUT=$out
    $env:GT_BENMORE_NANITE_VISUAL_REVIEW=$EvidenceRun
    $log=Join-Path $root "Saved/Logs/benmore_nanite_install_$stamp.log"
    $arguments=@(('"'+$root+'/GrandTour.uproject"'),'-NullRHI','-Unattended','-NoSplash','-NoSound',
        ('-ExecutePythonScript="'+$root+'/Art/Unreal/install_benmore_nanite.py"'),('-abslog="'+$log+'"'))
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    while(-not $process.WaitForExit(5000)){}
    $report=Get-Content -LiteralPath (Join-Path $out 'install-report.json') -Raw | ConvertFrom-Json
    if($process.ExitCode -ne 0 -or -not $report.ok){throw "Install failed; inspect $out and $log before further changes"}
    Write-Output "NANITE_INSTALL_OK $out"
} finally {
    $env:GT_BENMORE_NANITE_EVIDENCE=$oldEvidence
    $env:GT_BENMORE_NANITE_INSTALL_OUT=$oldOutput
    $env:GT_BENMORE_NANITE_VISUAL_REVIEW=$oldReview
    $mutex.ReleaseMutex();$mutex.Dispose()
}

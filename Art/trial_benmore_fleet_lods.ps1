param([switch]$Build,[switch]$Promote,[string]$EvidenceRun)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$held=$false
$oldOut=$env:GT_BENMORE_FLEET_LOD_OUT
$oldEvidence=$env:GT_BENMORE_FLEET_LOD_EVIDENCE
try {
    $deadline=[DateTime]::UtcNow.AddMinutes(30)
    Write-Output 'Waiting for the exclusive Unreal slot; no existing process will be closed.'
    while(-not $held){
        try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if([DateTime]::UtcNow -gt $deadline){throw 'Slot reservation timeout'}
    }
    function Get-Busy {
        @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealInsights|MSBuild|ShaderCompileWorker|cl|link)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
    }
    while(Get-Busy){
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing Unreal/build work did not finish'}
        Start-Sleep -Seconds 5
    }
    $stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
    if($Build){
        # Called in this runspace: the named mutex is recursive on this thread.
        & (Join-Path $PSScriptRoot 'build_guarded.ps1') *> (Join-Path $root ('Saved/Logs/benmore_far_lod_build_'+$stamp+'.txt'))
        if($LASTEXITCODE -ne 0){throw 'Rendering helper build failed; no editor launched'}
    }
    if(Get-Busy){throw 'Unexpected workload before trial launch'}
    $prefix='FleetLODTrial_'
    $script='trial_benmore_fleet_lods.py'
    if($Promote){
        if($EvidenceRun -notmatch '^\d{8}T\d{9}Z-[a-f0-9]{8}$'){throw 'Expected an evidence run ID'}
        $evidence=Join-Path $root ('Art/Export/BenmoreGaea/PerformanceRuns/'+$EvidenceRun)
        if(-not (Test-Path -LiteralPath (Join-Path $evidence 'profile-report.json'))){throw 'Comparison has not completed'}
        $env:GT_BENMORE_FLEET_LOD_EVIDENCE=$evidence
        $prefix='FleetLODPromote_';$script='promote_benmore_fleet_lods.py'
    }
    $out=Join-Path $root ('Art/Export/BenmoreGaea/'+$prefix+$stamp)
    $env:GT_BENMORE_FLEET_LOD_OUT=$out
    $arguments='"'+$root+'/GrandTour.uproject" -NullRHI -Unattended -NoSplash -NoSound -nop4 -ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'" -abslog="'+$out+'.log"'
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    $report=Get-Content -LiteralPath (Join-Path $out 'install-report.json') -Raw | ConvertFrom-Json
    if($process.ExitCode -ne 0 -or -not $report.ok){throw ('LOD trial failed; inspect saved asset rows before retry: '+$out)}
    Write-Output ('LOD asset operation completed; inspect report and verify normal driving: '+$out)
} finally {
    $env:GT_BENMORE_FLEET_LOD_OUT=$oldOut
    $env:GT_BENMORE_FLEET_LOD_EVIDENCE=$oldEvidence
    if($held){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}

param([ValidateSet('Install','Review','Reported')][string]$Mode='Install')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Another build/profile owns the Unreal slot'}
    # Independent headless gameplay checks may continue; they do not own this
    # editor or its materials. Never overlap another editor or asset commandlet.
    $editors=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor.*\.exe$' -and
        -not ($_.CommandLine -match '(?i)-game\b' -and $_.CommandLine -match '(?i)-NullRHI\b')
    })
    if($editors.Count){throw 'Another editor or asset commandlet is still active'}
    $script=if($Mode -eq 'Install'){'install_benmore_water_balanced.py'}else{'check_benmore_water_interaction.py'}
    $out=Join-Path $root 'Art/Export/BenmoreGaea/WaterBalanced_20261011'
    $oldReviewOut=$env:GT_WATER_REVIEW_OUT
    if($Mode -ne 'Install'){
        $env:GT_WATER_REVIEW_OUT=Join-Path $out ($Mode+'_'+(Get-Date -Format yyyyMMddTHHmmss))
        $report=Join-Path $env:GT_WATER_REVIEW_OUT 'vehicle-review.json'
    }else{$report=Join-Path $out 'install-report.json'}
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-NoP4','-GTNoLoad','-GTMorphology',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',
        ('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$out+'/'+$Mode+'.log"'))
    if($Mode -eq 'Reported'){$argsList+='-GTReportedCrossing'}
    if($Mode -ne 'Install'){$argsList+=@('-UseFixedTimeStep','-FPS=60')}
    $started=Get-Date
    $p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    if($p.ExitCode -ne 0){throw ('Editor failed: '+$p.ExitCode)}
    if(!(Test-Path -LiteralPath $report) -or (Get-Item -LiteralPath $report).LastWriteTime -lt $started){throw 'Missing or stale water report'}
    $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if(!$result.ok){throw $result.error}
    Write-Output ('BENMORE_WATER_BALANCED_OK '+$Mode+' '+$report)
} finally {
    if(Test-Path variable:oldReviewOut){$env:GT_WATER_REVIEW_OUT=$oldReviewOut}
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}

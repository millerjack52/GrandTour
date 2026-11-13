param([ValidateSet('Install','Verify')][string]$Mode='Install',[ValidateSet('Motion','Rapids','Detail')][string]$Variant='Motion')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
$previousVariant=$env:GT_WATER_ART_VARIANT
$env:GT_WATER_ART_VARIANT=$Variant
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Another build/profile owns the Unreal slot'}
    if(@(Get-Process UnrealEditor -ErrorAction SilentlyContinue).Count){throw 'Another editor is active'}
    $out=Join-Path $root ('Art/Export/BenmoreGaea/Water'+$Variant+'_20261011')
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $report=Join-Path $out $(if($Mode -eq 'Install'){'install-report.json'}else{'runtime-report.json'})
    $script=if($Mode -eq 'Install'){'install_benmore_water_motion.py'}else{'check_benmore_water_motion.py'}
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-NoP4','-GTNoLoad','-GTMorphology',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',
        ('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$out+'/'+$Mode+'.log"'))
    $started=Get-Date
    $p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    if($p.ExitCode -ne 0){throw ('Editor failed: '+$p.ExitCode)}
    if(!(Test-Path -LiteralPath $report) -or (Get-Item -LiteralPath $report).LastWriteTime -lt $started){throw 'Missing or stale motion report'}
    $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if(!$result.ok){throw $result.error}
    Write-Output ('BENMORE_WATER_MOTION_OK '+$report)
} finally {
    $env:GT_WATER_ART_VARIANT=$previousVariant
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}

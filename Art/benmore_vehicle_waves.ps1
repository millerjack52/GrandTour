param([ValidateSet('Tests','Review')][string]$Mode='Review',
    [string]$OutputFolder='VehicleWaves_20261011',[string]$Car='Ferrari288',[switch]$FoamFocus)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$out=Join-Path $root ('Art/Export/BenmoreGaea/'+$OutputFolder)
New-Item -ItemType Directory -Force -Path $out | Out-Null
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
$priorOut=$env:GT_WATER_REVIEW_OUT
$priorCar=$env:GT_WATER_REVIEW_CAR
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Another build/profile owns the Unreal slot'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An editor is active'}
    $env:GT_WATER_REVIEW_OUT=$out
    $env:GT_WATER_REVIEW_CAR='Benmore_Fleet_'+$Car
    $log=Join-Path $out ($Mode+'.log')
    $base=@(('"'+$root+'/GrandTour.uproject"'),'-Unattended','-NoSound','-NoSplash','-NoP4','-GTNoLoad',('-abslog="'+$log+'"'))
    if($Mode -eq 'Tests'){
        $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
        $argsList=$base+@('-NullRHI','-ExecCmds="Automation RunTests GrandTour.Water.RiverReference+GrandTour.Water.MovingDomain+GrandTour.Water.PassiveDetail+GrandTour.Water.InteractionVisuals"','-TestExit="Automation Test Queue Empty"')
    }else{
        $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
        $argsList=$base+@('-RenderOffScreen','-dx12','-GTMorphology','-GTPronouncedWaves','-UseFixedTimeStep','-FPS=60',
            '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
            '-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/check_benmore_water_interaction.py"'))
        if($FoamFocus){$argsList+='-GTFoamFocus'}
    }
    $started=Get-Date
    $p=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    if($p.ExitCode -ne 0){throw ('Editor failed: '+$p.ExitCode)}
    if((Get-Item -LiteralPath $log).LastWriteTime -lt $started){throw 'Stale check log'}
    if($Mode -eq 'Tests'){
        $rows=@(Select-String -LiteralPath $log -Pattern 'Test Completed\. Result=\{([^}]*)\}.*Path=\{(GrandTour\.Water\.[^}]*)\}')
        $rows | ForEach-Object {$_.Line}
        if($rows.Count -ne 4 -or @($rows | Where-Object {$_.Matches[0].Groups[1].Value -ne 'Success'}).Count){throw 'Water regression failed'}
    }else{
        $path=Join-Path $out 'vehicle-review.json'
        if((Get-Item -LiteralPath $path).LastWriteTime -lt $started){throw 'Stale vehicle report'}
        $report=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        if(!$report.ok -or !$report.fixed_dt.ok){throw ('Vehicle review failed: '+$report.error)}
    }
    Write-Output ('BENMORE_VEHICLE_WAVES_OK '+$Mode)
} finally {
    $env:GT_WATER_REVIEW_OUT=$priorOut
    $env:GT_WATER_REVIEW_CAR=$priorCar
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}

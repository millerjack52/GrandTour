param([ValidateSet('Water','Spray')][string]$Kind='Water',[switch]$WaitForSlot,
    [ValidateRange(1,90)][int]$MaxWaitMinutes=45)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$held=$false
$reservationDeadline=[DateTime]::UtcNow.AddMinutes($MaxWaitMinutes)
try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
if(-not $held -and $WaitForSlot){
    Write-Output 'Visual check queued for the exclusive Unreal slot.'
    while(-not $held -and [DateTime]::UtcNow -lt $reservationDeadline){
        try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
}
if(-not $held){$mutex.Dispose();throw 'Unreal slot reserved'}
$oldOut=$env:GT_BENMORE_VISUAL_OUT
try {
    function Get-Busy {
        @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealInsights|MSBuild|cl|link)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
    }
    $deadline=[DateTime]::UtcNow.AddMinutes($MaxWaitMinutes)
    while(Get-Busy){
        if(-not $WaitForSlot -or [DateTime]::UtcNow -gt $deadline){throw 'Unreal/build running; nothing launched'}
        Start-Sleep -Seconds 5
    }
    $out=Join-Path $root ('Art/Export/BenmoreGaea/'+$Kind+'Visual_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'))
    $env:GT_BENMORE_VISUAL_OUT=$out
    $common='"'+$root+'/GrandTour.uproject" -RenderOffScreen -dx12 -Unattended -NoSplash -nop4 -GTNoLoad -ResX=1600 -ResY=900 -ForceRes -abslog="'+$out+'.log"'
    if($Kind -eq 'Water'){
        $arguments=$common+' /Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview -game -windowed -ExecCmds="t.MaxFPS 60,py '+$root+'/Art/Unreal/review_benmore_optimised_visuals.py"'
        $reportName='visual-report.json'
    }else{
        $common=$common.Replace('-ResX=1600','-ResX=1440')
        $arguments=$common+' -UseFixedTimeStep -FPS=60 -NoSound -GTLookKuwahara=0 -ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False -ExecCmds="t.MaxFPS 30" -ExecutePythonScript="'+$root+'/Art/Unreal/review_benmore_spray_activation.py"'
        $reportName='check-report.json'
    }
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    # Each Python harness also has its own bounded timeout and normal quit.
    while(-not $process.WaitForExit(5000)){
        if([DateTime]::UtcNow -gt $deadline){throw ('Owned visual capture exceeded its bound; verify PID '+$process.Id+' before another launch')}
    }
    $file=Join-Path $out $reportName
    if(-not (Test-Path -LiteralPath $file)){throw ('Visual report missing: '+$out)}
    $report=Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
    if(-not $report.ok){throw ('Visual check failed: '+$out+' '+$report.error)}
    if($process.ExitCode -ne 0){throw ('Visual process exited abnormally: '+$out)}
    Write-Output ('Untimed visual check completed: '+$out)
} finally {
    $env:GT_BENMORE_VISUAL_OUT=$oldOut
    $mutex.ReleaseMutex();$mutex.Dispose()
}

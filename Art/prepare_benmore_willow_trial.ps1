param([switch]$WaitForSlot)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$held=$false
$deadline=[DateTime]::UtcNow.AddMinutes(60)
try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
if(-not $held -and $WaitForSlot){
    Write-Output 'Willow candidate preparation queued for the exclusive Unreal slot.'
    while(-not $held -and [DateTime]::UtcNow -lt $deadline){
        try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
}
if(-not $held){$mutex.Dispose();throw 'Unreal slot reserved'}
$old=$env:GT_BENMORE_WILLOW_TRIAL
try {
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealInsights|MSBuild|cl|link)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if($busy.Count){
            if(-not $WaitForSlot -or [DateTime]::UtcNow -gt $deadline){throw 'Unreal/build running; nothing launched'}
            Start-Sleep -Seconds 5
        }
    }while($busy.Count)
    $out=Join-Path $root ('Art/Export/BenmoreGaea/WillowTrial_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'))
    $env:GT_BENMORE_WILLOW_TRIAL=$out
    $arguments='"'+$root+'/GrandTour.uproject" -Unattended -NoSplash -NoSound -nop4 -RenderOffScreen -abslog="'+$out+'.log" -ExecutePythonScript="'+$root+'/Art/Unreal/prepare_benmore_willow_trial.py"'
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $limit=[DateTime]::UtcNow.AddMinutes(15)
    while(-not $process.WaitForExit(5000)){
        if([DateTime]::UtcNow -gt $limit){throw ('Preparation exceeded bound; verify owned PID '+$process.Id+' before another launch')}
    }
    $report=Get-Content -LiteralPath (Join-Path $out 'trial-report.json') -Raw | ConvertFrom-Json
    if(-not $report.ok -or $process.ExitCode -ne 0){throw ('Preparation failed: '+$out+' '+$report.error)}
    Write-Output ('Isolated willow trial ready: '+$out)
} finally {
    $env:GT_BENMORE_WILLOW_TRIAL=$old
    $mutex.ReleaseMutex();$mutex.Dispose()
}

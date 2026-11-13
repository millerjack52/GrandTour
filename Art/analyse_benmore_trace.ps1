param(
    [Parameter(Mandatory=$true)][string]$RunDirectory,
    [switch]$WaitForSlot,
    [ValidateRange(0,3600)][double]$StartSeconds=290,
    [ValidateRange(1,3600)][double]$EndSeconds=310
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$run=(Resolve-Path -LiteralPath $RunDirectory).Path
$runs=(Resolve-Path -LiteralPath (Join-Path $root 'Art/Export/BenmoreGaea/PerformanceRuns')).Path
if(-not $run.StartsWith($runs+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Expected an existing Benmore performance run'}
if($EndSeconds -le $StartSeconds){throw 'End must follow start'}
$trace=Join-Path $run 'timing.utrace'
if(-not (Test-Path -LiteralPath $trace)){throw 'Trace missing'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
if(-not $mutex.WaitOne(0)){$mutex.Dispose();throw 'Unreal slot reserved'}
try {
    function Get-BusyProcesses { @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealInsights|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }) }
    $busy=Get-BusyProcesses
    if($busy -and -not $WaitForSlot){throw 'Unreal/build running; analysis not launched'}
    $deadline=[DateTime]::UtcNow.AddMinutes(30)
    if($busy){Write-Output 'Reserved next slot for analysis; waiting for existing Unreal/build work. Nothing will be closed.'}
    while($busy){
        if([DateTime]::UtcNow -gt $deadline){throw 'Analysis slot wait timed out'}
        Start-Sleep -Seconds 5
        $busy=Get-BusyProcesses
    }
    $out=Join-Path $run ('Analysis_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'))
    New-Item -ItemType Directory -Path $out | Out-Null
    $commands=Join-Path $out 'commands.txt'
    $gpu=Join-Path $out 'gpu-statistics.csv'
    $cpu=Join-Path $out 'cpu-statistics.csv'
    $all=Join-Path $out 'all-thread-statistics.csv'
    # Insights treats backslashes in quoted response-file paths as escapes.
    $commandOut=$out.Replace('\','/')
    $commandGpu=$gpu.Replace('\','/')
    $commandCpu=$cpu.Replace('\','/')
    $commandAll=$all.Replace('\','/')
    # Each command is a separate line. Parenthesize concatenation when using
    # PowerShell arrays; a comma otherwise becomes part of the expression.
    [IO.File]::WriteAllLines($commands,[string[]]@(
        ('TimingInsights.ExportThreads "'+$commandOut+'/threads.csv"'),
        ('TimingInsights.ExportTimerStatistics "'+$commandGpu+'" -threads=GPU* -startTime='+$StartSeconds+' -endTime='+$EndSeconds),
        ('TimingInsights.ExportTimerStatistics "'+$commandCpu+'" -threads=GameThread,Render* -startTime='+$StartSeconds+' -endTime='+$EndSeconds),
        ('TimingInsights.ExportTimerStatistics "'+$commandAll+'" -threads=* -startTime='+$StartSeconds+' -endTime='+$EndSeconds),
        ('TimingInsights.ExportTimingEvents "'+$commandOut+'/worker-events.tsv" -threads=GameThread,Render*,Foreground*,Background* -columns=* -startTime='+$StartSeconds+' -endTime='+[Math]::Min($EndSeconds,$StartSeconds+1))
    ))
    # GUI executables do not synchronously wait under PowerShell's call operator.
    # Start-Process also preserves UE's required quotes *after* the equals sign.
    $arguments='-OpenTraceFile="'+$trace+'" -NoUI -AutoQuit -log -ABSLOG="'+$out+'/analysis.log" -ExecOnAnalysisCompleteCmd="@='+$commands+'"'
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealInsights.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    if($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $gpu) -or -not (Test-Path -LiteralPath $cpu) -or -not (Test-Path -LiteralPath $all)){throw ('Trace export incomplete: '+$out)}
    Write-Output $out
} finally {$mutex.ReleaseMutex();$mutex.Dispose()}

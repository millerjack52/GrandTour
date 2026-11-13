param([string]$Tag='grass_cooled',[int]$Frames=900)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$editor='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if (Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6 -ErrorAction SilentlyContinue) { throw 'An editor or game is running' }
$records=@()
$archive="$root\Art\Export\RoadFordStyle\GrassIterations\performance"
New-Item -ItemType Directory -Force $archive | Out-Null
$index=0
# ABBA limits order bias; no Unreal screenshots are requested or generated.
foreach ($mode in @('Off','On','On','Off')) {
    $index++
    $cool=[Diagnostics.Stopwatch]::StartNew()
    do {
        $gpu=(& nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits) -split ','
        if ([int]$gpu[0] -le 60 -and [int]$gpu[1] -le 25) { break }
        if ($cool.Elapsed.TotalSeconds -gt 180) { throw 'GPU did not cool sufficiently; profiling stopped' }
        Start-Sleep -Seconds 5
    } while ($true)
    $before=& nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active,clocks.gr,utilization.gpu --format=csv,noheader,nounits
    $log="$root\Saved\Logs\${Tag}_${index}_${mode}.log"
    $argsList=@(('"'+$root+'\GrandTour.uproject"'),"/Game/GrandTour/ArtTests/RoadFordStyle/L_GrassPerf_$mode",'-game','-RenderOffScreen','-unattended','-nosplash','-nosound','-GTNoLoad','-NoVSync','-ResX=1440','-ResY=900','-ForceRes','-windowed','-csvGpuStats',"-csvCaptureFrames=$Frames",'-ExitAfterCsvProfiling','-csvCompression=0','-GTLookKuwahara=0','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-abslog="'+$log+'"'))
    $start=Get-Date
    $proc=Start-Process -FilePath $editor -ArgumentList $argsList -WindowStyle Hidden -PassThru
    Write-Output "GRASS_PROFILE_STARTED $mode PID=$($proc.Id)"
    $telemetry=@()
    while (-not $proc.WaitForExit(3000)) {
        $telemetry+=(& nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active,clocks.gr,utilization.gpu --format=csv,noheader,nounits)
    }
    $after=& nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active,clocks.gr,utilization.gpu --format=csv,noheader,nounits
    $csv=Get-ChildItem "$env:LOCALAPPDATA\UnrealEngine\5.8\Saved\Profiling\CSV" -Filter '*.csv' | Where-Object LastWriteTime -gt $start | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $csv) { throw "No CSV from $mode; see $log" }
    $archivedCsv=Join-Path $archive "${Tag}_${index}_${mode}.csv"
    Copy-Item -LiteralPath $csv.FullName -Destination $archivedCsv
    $records+=@{mode=$mode;index=$index;exit=$proc.ExitCode;csv=$archivedCsv;log=$log;gpu_before=$before;gpu_after=$after;gpu_during=$telemetry;sample_start=300;sample_end=($Frames-50)}
    $records | ConvertTo-Json -Depth 5 | Set-Content "$root\Art\Export\RoadFordStyle\grass-profile-runs.json"
    Write-Output "GRASS_PROFILE_FINISHED $mode CSV=$($csv.Name)"
    if ($proc.ExitCode -ne 0) { throw "Unreal exited $($proc.ExitCode)" }
}

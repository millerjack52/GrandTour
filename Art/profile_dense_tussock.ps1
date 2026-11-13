param([int]$Frames=900,[int]$StartIndex=1)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$editor='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
$out="$root\Art\Export\DenseTussock\performance"; New-Item -ItemType Directory -Force $out|Out-Null
$records=@(); $index=0
if($StartIndex -gt 1){
    $records=@((Get-Content "$out\runs.json" -Raw|ConvertFrom-Json)|Where-Object index -lt $StartIndex)
    if($records.Count -ne ($StartIndex-1)){throw 'Missing earlier runs for resume'}
}
foreach($view in @('Driver','Overview')) {
 foreach($mode in @('LOD','Voxel','Preserve','Preserve','Voxel','LOD')) {
    $index++
    if($index -lt $StartIndex){continue}
    $cool=[Diagnostics.Stopwatch]::StartNew()
    do {
        $gpu=(& nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits)-split ','
        if([int]$gpu[0] -le 60 -and [int]$gpu[1] -le 25){break}
        if($cool.Elapsed.TotalSeconds -gt 180){throw 'GPU did not cool'}
        Start-Sleep -Seconds 5
    } while($true)
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW -ErrorAction SilentlyContinue){throw 'Editor or game appeared'}
    $log="$root\Saved\Logs\dense_${index}_${view}_${mode}.log"
    $arguments=@(('"'+$root+'\GrandTour.uproject"'),"/Game/GrandTour/ArtTests/DenseTussock/L_DT_${mode}_${view}",'-game','-RenderOffScreen','-dx12','-unattended','-nosplash','-nosound','-GTNoLoad','-NoVSync','-ResX=1440','-ResY=900','-ForceRes','-windowed','-csvGpuStats',"-csvCaptureFrames=$Frames",'-ExitAfterCsvProfiling','-csvCompression=0','-GTLookKuwahara=0','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-abslog="'+$log+'"'))
    $start=Get-Date; $telemetry=@()
    $p=Start-Process -FilePath $editor -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Write-Output "DENSE_PROFILE_STARTED $index $view $mode"
    while(-not $p.WaitForExit(3000)){
        if(Get-Process GrandTour,FarCry6,GoW -ErrorAction SilentlyContinue){
            Stop-Process -Id $p.Id -Force
            throw 'Another game started; stopped only the task-owned benchmark process'
        }
        $telemetry+=(& nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active,clocks.gr,utilization.gpu --format=csv,noheader,nounits)
    }
    if($p.ExitCode -ne 0){throw "Unreal exited $($p.ExitCode)"}
    if(Select-String $log -Pattern 'Failed to compile Material|LogMaterial: Error|Fatal error'){throw 'Material/runtime failure'}
    $csv=Get-ChildItem "$env:LOCALAPPDATA\UnrealEngine\5.8\Saved\Profiling\CSV" -Filter '*.csv'|Where-Object LastWriteTime -gt $start|Sort-Object LastWriteTime -Descending|Select-Object -First 1
    if(-not $csv){throw 'CSV missing'}
    $dest="$out\${index}_${view}_${mode}.csv"; Copy-Item -LiteralPath $csv.FullName -Destination $dest
    $records+=@{mode=$mode;view=$view;index=$index;csv=$dest;log=$log;gpu_during=$telemetry;sample_start=300;sample_end=($Frames-50)}
    $records|ConvertTo-Json -Depth 5|Set-Content "$out\runs.json"
    Write-Output "DENSE_PROFILE_FINISHED $index $view $mode"
 }
}

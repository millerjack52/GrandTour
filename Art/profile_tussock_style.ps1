$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$out="$root\Art\Export\TussockStyle\performance"
New-Item -ItemType Directory -Force $out|Out-Null
$records=@()
foreach($view in @('Driver','Overview')){
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
    $cool=[Diagnostics.Stopwatch]::StartNew()
    do{
        $gpu=(& nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits)-split ','
        if([int]$gpu[0] -le 60 -and [int]$gpu[1] -le 25){break}
        if($cool.Elapsed.TotalSeconds -gt 180){throw 'GPU did not cool'}
        Start-Sleep -Seconds 5
    }while($true)
    $suffix=if($view -eq 'Overview'){'_Overview'}else{''}
    $log="$root\Saved\Logs\tussock_style_profile_$view.log"
    $argsList=@(('"'+$root+'\GrandTour.uproject"'),('/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle'+$suffix),'-game','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-NoVSync','-ResX=1440','-ResY=900','-ForceRes','-windowed','-csvGpuStats','-csvCaptureFrames=900','-ExitAfterCsvProfiling','-csvCompression=0','-GTLookKuwahara=0','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-abslog="'+$log+'"'))
    $started=Get-Date; $telemetry=@()
    $p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
    Write-Output "TUSSOCK_PROFILE_STARTED $view"
    while(-not $p.WaitForExit(3000)){
        if(Get-Process GrandTour,GoW,FarCry6 -ErrorAction SilentlyContinue){Stop-Process -Id $p.Id -Force; throw 'Another game started; stopped task-owned benchmark'}
        $telemetry+=(& nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active,clocks.gr,utilization.gpu --format=csv,noheader,nounits)
    }
    if($p.ExitCode -ne 0){throw 'Unreal failed'}
    if(Select-String $log -Pattern 'Failed to compile Material|LogMaterial: Error|Fatal error'){throw 'Material/runtime failure'}
    $csv=Get-ChildItem "$env:LOCALAPPDATA\UnrealEngine\5.8\Saved\Profiling\CSV" -Filter '*.csv'|Where-Object LastWriteTime -gt $started|Sort-Object LastWriteTime -Descending|Select-Object -First 1
    if(-not $csv){throw 'CSV missing'}
    $dest="$out\$view.csv";Copy-Item -LiteralPath $csv.FullName -Destination $dest
    $records+=@{view=$view;csv=$dest;gpu_during=$telemetry;log=$log}
    ConvertTo-Json -InputObject @($records) -Depth 5|Set-Content "$out\runs.json"
    Write-Output "TUSSOCK_PROFILE_FINISHED $view"
}

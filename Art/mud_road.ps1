param([ValidateSet('Setup','Check')][string]$Mode='Check')
$ErrorActionPreference='Stop'
$labRoot=Split-Path $PSScriptRoot
$labOut=Join-Path $PSScriptRoot 'Export/MudRoad'
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Unreal slot is reserved by another task'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Close the running editor/game before running this check'}
    if($Mode -eq 'Setup'){
        & 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' "$labRoot/Art/tools/make_mud_road.py"
        if($LASTEXITCODE -ne 0){throw 'Numeric authoring failed'}
    }
    $labScript=if($Mode -eq 'Setup'){'setup_mud_road.py'}else{'check_mud_road.py'}
    $labReportName=if($Mode -eq 'Setup'){'setup-report.json'}else{'playtest-report.json'}
    $labArgs=@(('"'+$labRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',
        ('-ExecutePythonScript="'+$labRoot+'/Art/Unreal/'+$labScript+'"'),
        ('-abslog="'+$labRoot+'/Saved/Logs/MudRoad-'+$Mode+'.log"'))
    if($Mode -eq 'Setup'){$labArgs+='-NullRHI'}else{$labArgs+=@('-RenderOffScreen','-dx12')}
    $started=Get-Date
    $labStart=[Diagnostics.ProcessStartInfo]::new('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',($labArgs -join ' '))
    $labStart.UseShellExecute=$false;$labStart.CreateNoWindow=$true;$labStart.WindowStyle='Hidden'
    $labProcess=[Diagnostics.Process]::Start($labStart)
    if(-not $labProcess.WaitForExit(600000)){Stop-Process -Id $labProcess.Id;throw 'Owned Mud Road run exceeded ten minutes'}
    $labProcess.WaitForExit()
    $labExit=$labProcess.ExitCode
    $labFile=Get-Item -LiteralPath (Join-Path $labOut $labReportName)
    $labReport=Get-Content -LiteralPath $labFile.FullName -Raw | ConvertFrom-Json
    @{mode=$Mode;exit_code=$labExit;started=$started.ToString('o');report_written=$labFile.LastWriteTime.ToString('o');report_ok=$labReport.ok} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labOut ($Mode.ToLower()+'-process.json'))
    if($labExit -ne 0 -or $labFile.LastWriteTime -lt $started -or -not $labReport.ok){throw "Mud Road $Mode failed (exit=$labExit, report=$($labReport.ok)); inspect $($labFile.FullName)"}
    if($Mode -eq 'Check'){
        $labLog=Get-Content -LiteralPath "$labRoot/Saved/Logs/MudRoad-Check.log" -Raw
        if($labLog -notmatch 'Test Completed\. Result=\{Success\} Name=\{ShaderOracle\}') {throw 'Native C++ shader oracle did not pass'}
        if($labLog -match 'Failed to compile Material') {throw 'A material used a shader compilation fallback'}
    }
    Write-Output "Mud Road $Mode passed"
} finally {
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}


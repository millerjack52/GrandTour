param([ValidateSet('Setup','Check')][string]$Mode='Check',[switch]$DebugExit,[switch]$ProbeExit,[switch]$VisualOnly)
$ErrorActionPreference='Stop'
$labRoot=Split-Path $PSScriptRoot
$labOut=Join-Path $PSScriptRoot 'Export/MudRoad/MixedSurfaces'
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Unreal slot is reserved by another task'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Close the running editor/game before running this check'}
    $labScript=if($Mode -eq 'Setup'){'setup_mixed_route.py'}else{'check_mixed_route.py'}
    $labReportName=if($Mode -eq 'Setup'){'setup-report.json'}else{'playtest-report.json'}
    if($VisualOnly){$labReportName='visual-check-report.json'}
    $labRunName=if($VisualOnly){'Visual'}else{$Mode}
    $labArgs=@(('"'+$labRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',
        ('-ExecutePythonScript="'+$labRoot+'/Art/Unreal/'+$labScript+'"'),
        ('-abslog="'+$labRoot+'/Saved/Logs/MixedRoute-'+$labRunName+'.log"'))
    if($Mode -eq 'Setup'){$labArgs+='-NullRHI'}else{$labArgs+=@('-RenderOffScreen','-dx12')}
    if($ProbeExit){$labArgs+='-GTMudExitProbe'}
    if($VisualOnly){$labArgs+='-GTMixedVisualOnly'}
    $started=Get-Date
    $labStart=[Diagnostics.ProcessStartInfo]::new('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',($labArgs -join ' '))
    if($DebugExit){
        @{exe=$labStart.FileName;args=$labStart.Arguments} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labOut 'debug-args.json') -Encoding utf8
        $labStart=[Diagnostics.ProcessStartInfo]::new('C:/Users/mille/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',('"'+$labRoot+'/Art/tools/debug_mud_exit.py" "'+$labOut+'/debug-args.json"'))
    }
    $labStart.UseShellExecute=$false;$labStart.CreateNoWindow=$true;$labStart.WindowStyle='Hidden'
    $labProcess=[Diagnostics.Process]::Start($labStart)
    if(-not $labProcess.WaitForExit(600000)){Stop-Process -Id $labProcess.Id;throw 'Owned Mud Road run exceeded ten minutes'}
    $labProcess.WaitForExit()
    $labExit=$labProcess.ExitCode
    $labFile=Get-Item -LiteralPath (Join-Path $labOut $labReportName)
    $labReport=Get-Content -LiteralPath $labFile.FullName -Raw | ConvertFrom-Json
    @{mode=$labRunName;exit_code=$labExit;started=$started.ToString('o');report_written=$labFile.LastWriteTime.ToString('o');report_ok=$labReport.ok} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labOut ($labRunName.ToLower()+'-process.json'))
    if($labExit -ne 0 -or $labFile.LastWriteTime -lt $started -or -not $labReport.ok){throw "Mud Road $Mode failed (exit=$labExit, report=$($labReport.ok)); inspect $($labFile.FullName)"}
    if($Mode -eq 'Check' -and -not $VisualOnly){
        $labLog=Get-Content -LiteralPath "$labRoot/Saved/Logs/MixedRoute-Check.log" -Raw
        if($labLog -notmatch 'Test Completed\. Result=\{Success\} Name=\{ShaderOracle\}') {throw 'Native C++ shader oracle did not pass'}
        if($labLog -notmatch 'Test Completed\. Result=\{Success\} Name=\{SubstanceOracle\}') {throw 'Native C++ substance oracle did not pass'}
        foreach($required in @('GrassOracle','GranularSand','Emission')) {
            if($labLog -notmatch ('Test Completed\. Result=\{Success\} Name=\{'+$required+'\}')) {throw "$required did not pass"}
        }
        if($labLog -match 'Failed to compile Material') {throw 'A material used a shader compilation fallback'}
    }
    if($Mode -eq 'Check' -and (Get-Content -LiteralPath "$labRoot/Saved/Logs/MixedRoute-$labRunName.log" -Raw) -match 'Failed to compile Material') {throw 'A material used a shader compilation fallback'}
    Write-Output "Mud Road $Mode passed"
} finally {
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}



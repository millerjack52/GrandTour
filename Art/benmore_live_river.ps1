param([ValidateSet('Test','Install')][string]$Mode='Test')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Setup and CPU automation only. No timings or driving while the owner's game is running.
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Shared Unreal is occupied; wait for its owner to finish.'}
if(Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object {$_.CommandLine -like '*Art/suite.sh*'}){throw 'Shared suite is active between tests; wait for the whole suite.'}
$started=Get-Date
if($Mode -eq 'Test'){
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-ExecCmds="Automation RunTests GrandTour.Water.RiverReference"','-TestExit="Automation Test Queue Empty"',('-ReportExportPath="'+$root+'/Saved/Automation/BenmoreRiver"'),('-abslog="'+$root+'/Saved/Logs/BenmoreRiverTest.log"'))
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
}else{
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 15"',('-ExecutePythonScript="'+$root+'/Art/Unreal/install_benmore_live_river.py"'),('-abslog="'+$root+'/Saved/Logs/BenmoreLiveInstall.log"'))
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
}
$p=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
if($Mode -eq 'Test'){
    $r=Get-Content -LiteralPath ($root+'/Saved/Automation/BenmoreRiver/index.json') -Raw | ConvertFrom-Json
    if((Get-Item -LiteralPath ($root+'/Saved/Automation/BenmoreRiver/index.json')).LastWriteTime -lt $started){throw 'Stale test report'}
    if($r.failed -gt 0 -or $r.succeeded -lt 1){throw 'River automation failed; inspect BenmoreRiverTest.log'}
    Write-Output ('BENMORE_RIVER_TEST_OK: '+$r.succeeded+' CPU tests')
}else{
    $f=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/RiverScale/live-install-report.json')
    if($f.LastWriteTime -lt $started){throw 'No fresh setup report'}
    $r=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
    if(-not $r.ok){throw $r.error}
    Write-Output 'BENMORE_LIVE_RIVER_INSTALLED; stationary preview only, no driving or frame timings'
}

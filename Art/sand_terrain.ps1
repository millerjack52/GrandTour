# Run wait_unreal_free.ps1 separately before this runner.
param([ValidateSet('Setup','Review','Tests')][string]$Mode='Setup')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$out=Join-Path $PSScriptRoot 'Export/SandTerrain'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
    try {$acquired=$reservation.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Unreal slot reserved'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if($busy.Count){throw 'Unreal/build slot busy'}
    $started=Get-Date
    $scriptName=if($Mode -eq 'Setup'){'setup_sand_terrain.py'}else{'review_sand_terrain.py'}
    $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="ShowFlag.Rendering 0,landscape.Nanite.LiveRebuildOnModification 0,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',
        ('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),('-abslog="'+$projectRoot+'/Saved/Logs/SandTerrain-'+$Mode+'.log"'))
    if($Mode -eq 'Setup'){$editorArgs+='-NullRHI'}else{$editorArgs+=@('-RenderOffScreen','-dx12','-csvGpuStats')}
    if($Mode -eq 'Tests'){
        $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
            '-ExecCmds="Automation RunTests GrandTour.LandscapeMud+GrandTour.Mud.CarMud+GrandTour.DustLab.Emission"','-TestExit="Automation Test Queue Empty"',
            ('-ReportExportPath="'+$projectRoot+'/Saved/Automation/SandTerrain"'),('-abslog="'+$projectRoot+'/Saved/Logs/SandTerrain-Tests.log"'))
    }
    $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
    $ownedHandle=$p.Handle
    if(-not $p.WaitForExit(900000)){Stop-Process -Id $p.Id;throw 'Owned sand terrain run exceeded fifteen minutes'}
    $p.WaitForExit();$p.Refresh()
    $reportPath=if($Mode -eq 'Tests'){$projectRoot+'/Saved/Automation/SandTerrain/index.json'}else{$out+'/'+$Mode.ToLower()+'-report.json'}
    $file=Get-Item -LiteralPath $reportPath;$result=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    $okay=if($Mode -eq 'Tests'){$result.failed -eq 0 -and $result.succeeded -ge 14 -and $result.notRun -eq 0 -and ($result.tests.fullTestPath -contains 'GrandTour.LandscapeMud.GranularSand')}else{$result.ok}
    $status=@{mode=$Mode;exit_code=$p.ExitCode;report_ok=$okay;fresh=($file.LastWriteTime -ge $started);finished=(Get-Date).ToString('o')}
    $status | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath ($out+'/'+$Mode.ToLower()+'-run-status.json')
    if(-not $status.fresh -or -not $okay -or $p.ExitCode -ne 0){throw ('Sand terrain failed: '+($status | ConvertTo-Json -Compress))}
    Write-Output ('Sand terrain '+$Mode+' completed successfully')
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}





# Run wait_unreal_free.ps1 as a separate command first.
param([ValidateSet('Setup','Review','PropertiesReview')][string]$Mode='Setup',[switch]$Quick)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Unreal slot reserved'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if($busy.Count){throw 'Unreal/build slot busy'}
    $started=Get-Date
    $otherGameAtStart=@(Get-Process -Name Ace7Game -ErrorAction SilentlyContinue).Count -gt 0
    $scriptName=switch($Mode){'Review'{'review_mud_proving_ground.py'} 'PropertiesReview'{'review_mud_properties.py'} default{'setup_mud_proving_ground.py'}}
    $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="ShowFlag.Rendering 0,landscape.Nanite.LiveRebuildOnModification 0,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',
        ('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),
        ('-abslog="'+$projectRoot+'/Saved/Logs/MudProvingGround-'+$Mode+'.log"'))
    if($Mode -eq 'Setup'){$editorArgs+='-NullRHI'}else{$editorArgs+=@('-RenderOffScreen','-dx12','-csvGpuStats')}
    if($Quick){$editorArgs+='-GTMudProvingQuick'}
    $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
    $ownedProcessHandle=$p.Handle
    if(-not $p.WaitForExit(660000)){Stop-Process -Id $p.Id;throw 'Owned proving-ground run exceeded eleven minutes'}
    $p.WaitForExit()
    $p.Refresh()
    $file=Get-Item -LiteralPath ($projectRoot+'/Art/Export/MudProvingGround/'+$Mode.ToLower()+'-report.json')
    $result=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    $runStatus=@{mode=$Mode;exit_code=$p.ExitCode;report_ok=$result.ok;fresh=($file.LastWriteTime -ge $started);other_game_observed=($otherGameAtStart -or @(Get-Process -Name Ace7Game -ErrorAction SilentlyContinue).Count -gt 0);finished=(Get-Date).ToString('o')}
    $runStatus | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath ($projectRoot+'/Art/Export/MudProvingGround/'+$Mode.ToLower()+'-run-status.json')
    if($file.LastWriteTime -lt $started -or -not $result.ok -or $p.ExitCode -ne 0){throw ('Proving-ground run failed: exit='+$p.ExitCode+' report='+$result.ok+' fresh='+($file.LastWriteTime -ge $started)+'; inspect report and log')}
    Write-Output ('Mud proving ground '+$Mode+' completed; editor exit '+$p.ExitCode)
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

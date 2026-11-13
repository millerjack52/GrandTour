# Run wait_unreal_free.ps1 as a separate command first.
param([ValidateSet('Audit','Setup','Check')][string]$Mode='Setup')
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
    $scriptName=if($Mode -eq 'Check'){'check_mud_route_response.py'}else{'rebuild_mud_variants_response.py'}
    $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-UseFixedTimeStep','-FPS=60',
        '-ExecCmds="landscape.Nanite.LiveRebuildOnModification 0"',
        ('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),
        ('-abslog="'+$projectRoot+'/Saved/Logs/MudVariantsResponse-'+$Mode+'.log"'))
    if($Mode -eq 'Audit'){$editorArgs+='-GTMudVariantsAudit'}
    $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
    # CL2: the Check now also drives the clay lane and the two mud lanes through three passes each (about twenty minutes of play at worst), so it gets 30 minutes; Setup and Audit keep eleven.
    $limitMs=if($Mode -eq 'Check'){1800000}else{660000}
    if(-not $p.WaitForExit($limitMs)){Stop-Process -Id $p.Id;throw ('Owned mud variants run exceeded '+($limitMs/60000)+' minutes')}
    $file=Get-Item -LiteralPath ($projectRoot+'/Art/Export/MudVariants/response-'+$Mode.ToLower()+'-report.json')
    $result=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    if($file.LastWriteTime -lt $started -or -not $result.ok -or $p.ExitCode -ne 0){throw 'Mud variants run failed; inspect report and log'}
    Write-Output ('Mud variants '+$Mode+' passed; editor exit '+$p.ExitCode)
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

# Build and capture the isolated Mackenzie river reach. Run wait_unreal_free.ps1 first.
param([switch]$DriveReview)

$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    # Run this script only after wait_unreal_free.ps1 has returned 0 as its own command.
    try {$acquired=$reservation.WaitOne(0)}
    catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Unreal slot reserved by another task'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($busy.Count){throw 'Unreal/build slot became busy; run wait_unreal_free.ps1 again'}
    $started=Get-Date
    $scriptName='setup_mackenzie_river_study.py'
    $logName='MackenzieRiverStudy.log'
    $reportName='study-report.json'
    if($DriveReview){$scriptName='check_mackenzie_river_drive.py';$logName='MackenzieRiverDrive.log';$reportName='drive-report.json'}
    $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLook=0','-GTLookSky=0','-GTLookHaze=0',
        '-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1,landscape.Nanite.LiveRebuildOnModification 0"',
        ('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),
        ('-abslog="'+$projectRoot+'/Saved/Logs/'+$logName+'"'))
    if($DriveReview){$editorArgs+=@('-UseFixedTimeStep','-FPS=60')}
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
    $process.WaitForExit()
    $report=Get-Item -LiteralPath ($projectRoot+'/Art/Export/MackenzieRiverStudy/'+$reportName)
    if($report.LastWriteTime -lt $started){throw ('No fresh review report; inspect Saved/Logs/'+$logName)}
    $capture=Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json
    $statusName=if($DriveReview){'drive-run-status.json'}else{'run-status.json'}
    @{editor_exit_code=$process.ExitCode;review_completed=$capture.ok;clean_editor_exit=($process.ExitCode -eq 0);capture_report=$report.FullName} | ConvertTo-Json | Set-Content -LiteralPath ($projectRoot+'/Art/Export/MackenzieRiverStudy/'+$statusName)
    if($DriveReview){$capture | Select-Object ok,error,fixed_dt,images | ConvertTo-Json -Depth 4}else{Get-Content -LiteralPath $report.FullName}
    if($process.ExitCode -ne 0){throw ('Editor exited '+$process.ExitCode+'; review and exit statuses are recorded separately in '+$statusName)}
    if(-not (Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json).ok){throw 'Scene/capture failed; inspect report'}
} finally {
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}

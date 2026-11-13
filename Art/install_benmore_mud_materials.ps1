# Integrate approved material layers into Benmore. Run wait_unreal_free.ps1 first.
param([switch]$Inspect)
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
    $scriptName=if($Inspect){'inspect_benmore_mud_materials.py'}else{'install_benmore_mud_materials.py'}
    $logName='BenmoreMudMaterials.log'
    $reportName=if($Inspect){'inventory.json'}else{'install-report.json'}
    $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1,landscape.Nanite.LiveRebuildOnModification 0"',
        ('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),
        ('-abslog="'+$projectRoot+'/Saved/Logs/'+$logName+'"'))
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
    $process.WaitForExit()
    if($process.ExitCode -ne 0){throw ('Editor exited '+$process.ExitCode)}
    $report=Get-Item -LiteralPath ($projectRoot+'/Art/Export/BenmoreMudMaterials/'+$reportName)
    if($report.LastWriteTime -lt $started){throw 'No fresh setup report; inspect Saved/Logs/BenmoreMudMaterials.log'}
    Get-Content -LiteralPath $report.FullName
    if(-not $Inspect -and -not (Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json).ok){throw 'Scene/capture failed; inspect report'}
} finally {
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}

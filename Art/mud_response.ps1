# Set up or review the isolated surface-response scene. Run wait_unreal_free.ps1 first.
param([switch]$Review,[switch]$SetupAndReview,[switch]$Tests,[switch]$PhysicsOnly,[switch]$CaptureLite,[switch]$DrivingOnly,[switch]$Profile,[switch]$ProfileDriving,[switch]$Dynamics,[switch]$Baseline,[switch]$Materials,[ValidateRange(0,2)][int]$Quality=1)
$ErrorActionPreference='Stop'
if($ProfileDriving){$Profile=$true}
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
    $scriptName=if($Review -or $PhysicsOnly){'review_mud_response.py'}else{'setup_mud_response.py'}
    if($Profile){$scriptName='profile_mud_response.py'}
    if($Dynamics){$scriptName='check_mud_dynamics.py'}
    if($Materials){$scriptName='refresh_mud_response_ground.py'}
    $logName='MudResponse.log'
    $reportName=if($Review -or $SetupAndReview){'review-report.json'}else{'setup-report.json'}
    if($PhysicsOnly){$reportName='contact-report.json'}
    if($Dynamics){$reportName=if($Baseline){'dynamics-before.json'}else{'dynamics-after.json'}}
    if($Profile){$reportName=if($ProfileDriving){'scalability-driving-report.json'}else{'scalability-report.json'}}
    if($Materials){$reportName='material-report.json'}
    $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-UseFixedTimeStep','-FPS=60','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="ShowFlag.Rendering 0,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1,landscape.Nanite.LiveRebuildOnModification 0"',
        ('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),
        ('-abslog="'+$projectRoot+'/Saved/Logs/'+$logName+'"'))
    if($SetupAndReview){$editorArgs+='-GTMudResponseReview'}
    if($PhysicsOnly){$editorArgs+=@('-NullRHI','-GTMudResponsePhysicsOnly')}
    if($Materials){$editorArgs+='-NullRHI'}
    if($Dynamics){$editorArgs+='-NullRHI';if($Baseline){$editorArgs+='-GTMudDynamicsBaseline'}}
    if($DrivingOnly){$editorArgs+='-GTMudResponseDrivingOnly'}
    if($CaptureLite){
        $editorArgs=$editorArgs | Where-Object {$_ -notlike '-ExecCmds=*'}
        $editorArgs+=@('-GTMudResponseCaptureLite','-ExecCmds="ShowFlag.Rendering 0,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1,landscape.Nanite.LiveRebuildOnModification 0,r.Shadow.Virtual.Enable 0,r.Shadow.MaxResolution 1024,r.Shadow.CSM.MaxCascades 2,r.Lumen.HardwareRayTracing 0,r.RayTracing.ForceAllRayTracingEffects 0"')
    }
    $editorArgs=$editorArgs | ForEach-Object {
        if($_ -like '-ExecCmds=*') { $_.Replace('ShowFlag.Rendering 0',('ShowFlag.Rendering 0,gt.LandscapeMud.Quality '+$Quality)) } else { $_ }
    }
    if($Profile){
        $editorArgs=$editorArgs | Where-Object {$_ -notin @('-UseFixedTimeStep','-FPS=60')}
        $editorArgs+='-csvGpuStats'
        if($ProfileDriving){$editorArgs+='-GTMudProfileDriving'}
    }
    if($Tests){
        $editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
            '-ExecCmds="Automation RunTests GrandTour.LandscapeMud"','-TestExit="Automation Test Queue Empty"',
            ('-ReportExportPath="'+$projectRoot+'/Saved/Automation/LandscapeMud"'),('-abslog="'+$projectRoot+'/Saved/Logs/LandscapeMudTests.log"'))
    }
    $process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
    if($Profile){
        # Bound only the process launched by this runner; other editors are never touched.
        if(-not $process.WaitForExit(240000)){
            Stop-Process -Id $process.Id
            throw 'Mud profile exceeded four minutes; owned review process stopped. Inspect partial report/log.'
        }
    } else {
        # The Python deadline cannot fire while the render thread blocks its callback.
        if(-not $process.WaitForExit(660000)){
            Stop-Process -Id $process.Id
            throw 'Mud review exceeded eleven minutes; owned review process stopped. Inspect partial report/log.'
        }
    }
    if($Tests){
        $testFile=Get-Item -LiteralPath ($projectRoot+'/Saved/Automation/LandscapeMud/index.json')
        $testsResult=Get-Content -LiteralPath $testFile.FullName -Raw | ConvertFrom-Json
        if($testFile.LastWriteTime -lt $started -or $process.ExitCode -ne 0 -or $testsResult.failed -gt 0 -or $testsResult.succeeded -lt 1 -or $testsResult.notRun -gt 0){throw 'Landscape mud automation failed; inspect Saved/Automation/LandscapeMud'}
        Write-Output ('Landscape mud tests passed: '+$testsResult.succeeded);exit 0
    }
    if($Dynamics -and -not $Baseline){
        & 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' ($projectRoot+'/Art/tools/check_mud_dynamics_report.py')
        if($LASTEXITCODE -ne 0){throw 'Unrestricted mud driving acceptance failed; inspect dynamics-after.json'}
    }
    $report=Get-Item -LiteralPath ($projectRoot+'/Art/Export/MudResponse/'+$reportName)
    if($report.LastWriteTime -lt $started){throw 'No fresh setup report; inspect Saved/Logs/MudResponse.log'}
    $result=Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json
    if($Profile){$result | Add-Member -NotePropertyName editor_exit_code -NotePropertyValue $process.ExitCode -Force; $result | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $report.FullName -Encoding UTF8}
    if(-not $result.ok){throw 'Scene/capture failed; inspect report'}
    Write-Output ('Mud response completed; '+$result.images.Count+' captures. Editor exit: '+$process.ExitCode)
    if($process.ExitCode -ne 0){Write-Warning 'Editor exited abnormally after successful save/captures; inspect the shutdown log.'}
} finally {
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}

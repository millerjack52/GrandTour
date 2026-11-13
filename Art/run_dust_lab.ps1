# Separate process only, holding the established shared Unreal reservation.
# Never closes another process. BenmoreSetup explicitly installs into the main
# level; prototype setup modes write their private DustLab assets.
param([ValidateSet('Build','Setup','Review','Tests','SprayTests','Verify','MudSetup','MudReview','MudVerify','BenmoreSetup','BenmoreReview','BenmoreVerify')][string]$Mode='Setup')
$ErrorActionPreference='Stop'
$dustRoot=Split-Path $PSScriptRoot
$dustMutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$dustAcquired=$false
try {
    try {$dustAcquired=$dustMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$dustAcquired=$true}
    if(-not $dustAcquired){throw 'DustLab deferred: another task owns the shared Unreal slot.'}
    $dustBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($dustBusy.Count){throw ('DustLab deferred: '+(($dustBusy | ForEach-Object { $_.Name+'#'+$_.ProcessId }) -join ', '))}
    # These are functional captures, not performance runs. Other applications
    # remain untouched; do not interpret fixed-step frame times as measurements.
    $dustOut=Join-Path $dustRoot 'Art\Export\DustLab'
    New-Item -ItemType Directory -Path $dustOut -Force | Out-Null
    if($Mode -eq 'Build') {
        # Promote only this prototype's new files while holding the shared slot.
        # Never overwrite another task's file, including a changed earlier install.
        $dustStage=Join-Path $dustRoot 'Art\DustLab\PendingSource'
        $dustSources=@('Source\GrandTour\Vehicle\GTDustLab.h','Source\GrandTour\Vehicle\GTDustLab.cpp',
            'Source\GrandTour\Vehicle\GTDustLabTests.cpp','Source\GrandTourEditor\Private\FX\GTDustLabSetupLibrary.h',
            'Source\GrandTourEditor\Private\FX\GTDustLabSetupLibrary.cpp',
            'Source\GrandTour\Vehicle\GTMudFlickLab.h','Source\GrandTour\Vehicle\GTMudFlickLab.cpp','Source\GrandTour\Vehicle\GTMudFlickLabTests.cpp',
            'Source\GrandTour\Vehicle\GTVehicleSurfaceEffects.h','Source\GrandTour\Vehicle\GTVehicleSurfaceEffects.cpp')
        foreach($dustRelative in $dustSources) {
            $dustSource=Join-Path $dustStage $dustRelative
            $dustTarget=Join-Path $dustRoot $dustRelative
            if(-not (Test-Path -LiteralPath $dustSource)){throw ('Missing staged source '+$dustRelative)}
            if((Test-Path -LiteralPath $dustTarget) -and (Get-FileHash -LiteralPath $dustTarget).Hash -ne (Get-FileHash -LiteralPath $dustSource).Hash){throw ('Refusing to overwrite '+$dustTarget)}
        }
        foreach($dustRelative in $dustSources) {
            $dustTarget=Join-Path $dustRoot $dustRelative
            New-Item -ItemType Directory -Path (Split-Path $dustTarget) -Force | Out-Null
            if(-not (Test-Path -LiteralPath $dustTarget)){Copy-Item -LiteralPath (Join-Path $dustStage $dustRelative) -Destination $dustTarget}
        }
        & 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat' GrandTourEditor Win64 Development ('-Project='+$dustRoot+'\GrandTour.uproject') -WaitMutex 2>&1 | Tee-Object -FilePath (Join-Path $dustOut 'Build.log')
        if($LASTEXITCODE -ne 0){throw ('DustLab build failed with exit '+$LASTEXITCODE)}
        Write-Output 'DUSTLAB_BUILD_OK'
        exit 0
    }
    $dustStarted=Get-Date
    $dustArgs=@(('"'+$dustRoot+'\GrandTour.uproject"'),'/Engine/Maps/Entry','-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ResX=1440','-ResY=900',('-abslog="'+$dustOut+'\'+$Mode+'.log"'))
    if($Mode -match 'Tests$') {
        $dustFilter=if($Mode -eq 'SprayTests'){'GrandTour.Spray'}else{'GrandTour.DustLab'}
        $dustArgs+=@('-NullRHI',('-ExecCmds="Automation RunTests '+$dustFilter+'"'),'-TestExit="Automation Test Queue Empty"',('-ReportExportPath="'+$dustOut+'\'+$Mode+'"'))
    } elseif($Mode -match 'Verify$') {
        $dustReport=if($Mode -eq 'MudVerify'){'mud-verify-report.json'}else{'verify-report.json'}
        $dustVerify=if($Mode -eq 'MudVerify'){'verify_mud_flick_lab.py'}else{'verify_dust_lab_install.py'}
        if($Mode -eq 'BenmoreVerify'){$dustVerify='verify_benmore_surface_fx.py';$dustReport='benmore-verify-report.json'}
        $dustArgs+=@('-NullRHI','-run=pythonscript',('-script="'+$dustRoot+'\Art\Unreal\'+$dustVerify+'"'))
    } else {
        $dustScript=if($Mode -eq 'Setup'){'setup_dust_lab.py'}else{'review_dust_lab.py'}
        $dustReport=if($Mode -eq 'Setup'){'setup-report.json'}else{'review-report.json'}
        if($Mode -eq 'MudSetup'){$dustScript='setup_mud_flick_lab.py';$dustReport='mud-setup-report.json'}
        if($Mode -eq 'MudReview'){$dustScript='review_mud_flick_lab.py';$dustReport='mud-review-report.json'}
        if($Mode -eq 'BenmoreSetup'){$dustScript='setup_benmore_surface_fx.py';$dustReport='benmore-setup-report.json'}
        if($Mode -eq 'BenmoreReview'){$dustScript='review_benmore_surface_fx.py';$dustReport='benmore-review-report.json'}
        $dustArgs+=('-ExecutePythonScript="'+$dustRoot+'\Art\Unreal\'+$dustScript+'"')
        # Author with a renderer so Niagara's runtime-readiness check is meaningful.
        if($Mode -eq 'BenmoreReview') {
            $dustArgs+=@('-UseFixedTimeStep','-FPS=30','-BENCHMARK','-ExecCmds="r.ScreenPercentage 60,r.Lumen.DiffuseIndirect.Allow 0,r.Lumen.Reflections.Allow 0,r.ShadowQuality 2,r.VolumetricCloud 0"')
        } elseif($Mode -match 'Review$'){$dustArgs+=@('-UseFixedTimeStep','-FPS=60','-BENCHMARK')}
    }
    $dustProcess=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $dustArgs -WindowStyle Hidden -PassThru -Wait
    if($dustProcess.ExitCode -ne 0){throw ('DustLab '+$Mode+' editor exit '+$dustProcess.ExitCode)}
    if($Mode -match 'Setup$') {
        $dustFirst=Get-Content -LiteralPath (Join-Path $dustOut $dustReport) -Raw | ConvertFrom-Json
        if($dustFirst.ok -and $dustFirst.install_pending) {
            # SaveMap leaves the source world open. Install only after reopening
            # the newly saved copy in a fresh process under this same reservation.
            $dustStarted=Get-Date
            $dustProcess=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $dustArgs -WindowStyle Hidden -PassThru -Wait
            if($dustProcess.ExitCode -ne 0){throw ('DustLab install editor exit '+$dustProcess.ExitCode)}
        }
    }
    if($Mode -match 'Tests$') {
        $dustTestFile=Get-Item -LiteralPath (Join-Path $dustOut ($Mode+'\index.json')) -ErrorAction Stop
        if($dustTestFile.LastWriteTime -lt $dustStarted){throw 'No fresh DustLab test report.'}
        $dustTests=Get-Content -LiteralPath $dustTestFile.FullName -Raw | ConvertFrom-Json
        if($dustTests.failed -gt 0 -or ($dustTests.succeeded+$dustTests.succeededWithWarnings) -lt 1 -or $dustTests.notRun -gt 0){throw 'DustLab automation tests did not pass.'}
        $dustRequiredNames=if($Mode -eq 'Tests'){@('GrandTour.DustLab.Emission','GrandTour.DustLab.MudFlick')}else{@()}
        foreach($dustRequiredTest in $dustRequiredNames) {
            if(-not ($dustTests.tests | Where-Object {$_.fullTestPath -eq $dustRequiredTest -and $_.state -eq 'Success'})){throw ('Required test did not succeed: '+$dustRequiredTest)}
        }
    } else {
        $dustFile=Get-Item -LiteralPath (Join-Path $dustOut $dustReport) -ErrorAction Stop
        if($dustFile.LastWriteTime -lt $dustStarted){throw 'No fresh DustLab report.'}
        $dustResult=Get-Content -LiteralPath $dustFile.FullName -Raw | ConvertFrom-Json
        if(-not $dustResult.ok){throw $dustResult.error}
    }
    Write-Output ('DUSTLAB_'+$Mode.ToUpper()+'_OK')
} finally {
    if($dustAcquired){$dustMutex.ReleaseMutex()}
    $dustMutex.Dispose()
}

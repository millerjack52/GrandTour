param([switch]$Gather,[switch]$ForceRulesCompile)
# Keep the shared profiling reservation for the entire build, closing the
# check-then-launch race between Art/build.sh and the profiling runner.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    try {$acquired=$mutex.WaitOne(0)}
    catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){Write-Output 'BUILD BLOCKED: Benmore profiling owns the Unreal slot'; exit 2}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealInsights|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($busy.Count){Write-Output 'BUILD BLOCKED: Unreal, Insights or a build is running'; exit 2}
    $buildArguments=@('GrandTourEditor','Win64','Development',('-Project='+$root+'/GrandTour.uproject'),'-WaitMutex')
    if($Gather){$buildArguments+='-gather'}
    # UE 5.8's timestamp check otherwise overwrites ForceRulesCompile for installed rules.
    if($ForceRulesCompile){$buildArguments+=@('-ForceRulesCompile','-SkipRulesCompile')}
    & 'C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat' @buildArguments
    exit $LASTEXITCODE
} finally {
    if($acquired){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}

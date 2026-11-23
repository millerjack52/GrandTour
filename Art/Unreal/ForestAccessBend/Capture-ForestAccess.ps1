[CmdletBinding()]
param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..\..\..'),
    [Parameter(Mandatory)][ValidateSet('baseline','candidate')][string]$Stage,
    [switch]$Motion,
    [switch]$SunsetStudy,
    [switch]$BroadleafStudy,
    [switch]$OriginalBroadleaf,
    [switch]$TimingOnly,
    [switch]$SavedBaseline
)
$ErrorActionPreference = 'Stop'
$project = Get-Item -LiteralPath (Join-Path $ProjectRoot 'GrandTour.uproject')
if($SavedBaseline -and $Stage -ne 'baseline'){throw 'The saved baseline can only be used for a baseline drive.'}
$reviewSettings=Join-Path $project.DirectoryName 'Saved_ForestAccessReview\Config\WindowsEditor'
$null=New-Item -ItemType Directory -Path $reviewSettings -Force
$liveSettings=Join-Path $project.DirectoryName 'Saved\Config\WindowsEditor\GameUserSettings.ini'
if(Test-Path -LiteralPath $liveSettings){Copy-Item -LiteralPath $liveSettings -Destination $reviewSettings -Force}
$output = Join-Path $project.DirectoryName ('Saved\ForestAccessBend\drives\'+$Stage+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$null = New-Item -ItemType Directory -Path $output -Force
$previousOutput = $env:GT_BEND_DRIVE_OUTPUT
$previousScript = $env:GT_BEND_DRIVE_SCRIPT
$previousMotion = $env:GT_BEND_MOTION
$previousSunset = $env:GT_BEND_SUNSET
$previousCrown = $env:GT_BEND_CROWN_STUDY
$previousOriginal = $env:GT_BEND_ORIGINAL_CROWN
$previousTiming = $env:GT_BEND_TIMING_ONLY
$previousMap = $env:GT_BEND_DRIVE_MAP
$normalMap='/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy'
$env:GT_BEND_DRIVE_MAP=$normalMap
$env:GT_BEND_MOTION = [int]$Motion.IsPresent
$env:GT_BEND_SUNSET = [int]$SunsetStudy.IsPresent
$env:GT_BEND_CROWN_STUDY = [int]$BroadleafStudy.IsPresent
$env:GT_BEND_ORIGINAL_CROWN = [int]$OriginalBroadleaf.IsPresent
$env:GT_BEND_TIMING_ONLY = [int]$TimingOnly.IsPresent
$env:GT_BEND_DRIVE_OUTPUT = $output
$env:GT_BEND_DRIVE_SCRIPT = (Join-Path $PSScriptRoot 'capture-bend.py').Replace('\','/')
function Start-Process($FilePath,$ArgumentList) {
    if (Get-Process UnrealEditor*,blender,Wardogs* -ErrorAction SilentlyContinue) {throw 'Another renderer is active'}
    $params = foreach($entry in $ArgumentList) {
        if($entry -eq $normalMap) { $env:GT_BEND_DRIVE_MAP }
        elseif($entry -like '-ExecCmds=*') { $entry.TrimEnd('"')+',py '+$env:GT_BEND_DRIVE_SCRIPT+'"' }
        elseif($entry -like '-abslog=*') { '-abslog="'+(Join-Path $env:GT_BEND_DRIVE_OUTPUT 'standalone.log')+'"' }
        else { $entry }
    }
    $params+=@('-ForceEnablePython','-Unattended','-NoSound','-RenderOffScreen','-ForceRes','-saveddirsuffix=ForestAccessReview','-NoSplash','-NoAutoSave')
    $job=Microsoft.PowerShell.Management\Start-Process -FilePath $FilePath -ArgumentList $params -WindowStyle Hidden -PassThru
    $job.WaitForExit()
    if($job.ExitCode -ne 0){ throw "Unreal exited with code $($job.ExitCode)" }

}
$launcher = Join-Path $project.DirectoryName 'Art\open_lidar_study.ps1'
try {
    if($SavedBaseline){
        $receipt=Get-Content -LiteralPath (Join-Path $project.DirectoryName 'Saved/ForestAccessBend/build.json') -Raw | ConvertFrom-Json
        $backup=Join-Path $project.DirectoryName 'Saved/ForestAccessBend/BeforeForestAccess.umap'
        if((Get-FileHash -LiteralPath $backup).Hash -ne $receipt.source_sha256){throw 'The original map backup failed its checksum.'}
        $tempName='ForestAccessReview_'+[guid]::NewGuid().ToString('N')
        $copyFolder=New-Item -ItemType Directory -Path (Join-Path $project.DirectoryName ('Content/'+$tempName))
        $copyMap=Join-Path $copyFolder.FullName 'L_LidarStudy.umap'
        Copy-Item -LiteralPath $backup -Destination $copyMap
        $env:GT_BEND_DRIVE_MAP='/Game/'+$tempName+'/L_LidarStudy'
    }
    & $launcher -Play
} finally {
    $env:GT_BEND_DRIVE_OUTPUT = $previousOutput
    $env:GT_BEND_DRIVE_SCRIPT = $previousScript
    $env:GT_BEND_MOTION = $previousMotion
    $env:GT_BEND_SUNSET = $previousSunset
    $env:GT_BEND_CROWN_STUDY = $previousCrown
    $env:GT_BEND_ORIGINAL_CROWN = $previousOriginal
    $env:GT_BEND_TIMING_ONLY = $previousTiming
    $env:GT_BEND_DRIVE_MAP = $previousMap
    if ($copyMap -and (Test-Path -LiteralPath $copyMap)){Remove-Item -LiteralPath $copyMap}
    if ($copyFolder -and !(Get-ChildItem -LiteralPath $copyFolder.FullName -Force)){Remove-Item -LiteralPath $copyFolder.FullName}
}
if(Test-Path -LiteralPath (Join-Path $output 'error.txt')) { throw (Get-Content -LiteralPath (Join-Path $output 'error.txt') -Raw) }
$report=Get-Item -LiteralPath (Join-Path $output 'drive.json') -ErrorAction SilentlyContinue
if(!$report){throw "Unreal produced no drive report at $output"}
if(!(Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json).ok) {throw 'The pickup did not complete the bend.'}
if(!(Get-ChildItem -LiteralPath $output -Filter 'timing.csv*')) {throw "The drive completed but the GPU timing trace is missing from $output"}
$output

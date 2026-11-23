[CmdletBinding()]
param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..\..\..'),
    [string]$EditorCmd = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe',
    [switch]$Preview,
    [switch]$PreviewOnly,
    [switch]$VerifyOnly,
    [switch]$Broadleaf
)
$ErrorActionPreference='Stop'
$project=Get-Item -LiteralPath (Join-Path $ProjectRoot 'GrandTour.uproject')
$map='/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy'
$reportDir=Join-Path $project.DirectoryName 'Saved\ForestAccessBend'
function Show-Bend {
    if (Get-Process UnrealEditor*,blender,Wardogs* -ErrorAction SilentlyContinue) {throw 'Another renderer is active.'}
    $quality=Get-Content -LiteralPath (Join-Path $project.DirectoryName 'Art\lidar_performance.json') -Raw | ConvertFrom-Json
    $view=Get-Content -LiteralPath (Join-Path $reportDir 'build.json') -Raw | ConvertFrom-Json
    $cmds=@($quality.commands)+@('EnableCheats',('BugItGo '+($view.approach -join ' ')+' 0 '+$view.yaw+' 0'))
    $app=Join-Path (Split-Path -Parent $EditorCmd) 'UnrealEditor.exe'
    $runArgs=@(('"'+$project.FullName+'"'),$map,'-game','-GTNoLoad','-GTLookKuwahara=0','-windowed','-ResX=1600','-ResY=900',('-ExecCmds="'+($cmds -join ',')+'"'))
    Start-Process -FilePath $app -ArgumentList $runArgs
}
if($PreviewOnly){Show-Bend;return}
$authoring=Join-Path $PSScriptRoot 'forest_access.py'
foreach($path in @($EditorCmd,$authoring,(Join-Path $project.DirectoryName 'Art\Unreal\lidar_grounding.py'))) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) {throw "Missing file: $path"}
}
$null=New-Item -ItemType Directory -Path $reportDir -Force
$python=Join-Path $project.DirectoryName 'Saved\Tools\TerrainPython\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) {$python='python'}
if (!$VerifyOnly -and (!(Test-Path -LiteralPath (Join-Path $reportDir 'T_BendMossShoots.tga')) -or
                       !(Test-Path -LiteralPath (Join-Path $reportDir 'T_ForestAccessFloor.tga')) -or
                       !(Test-Path -LiteralPath (Join-Path $reportDir 'T_BendMossLitterFields.tga')))) {
    & $python (Join-Path $PSScriptRoot 'bake_floor.py') --output-dir $reportDir
    if ($LASTEXITCODE -ne 0) {throw 'The forest floor texture bake failed.'}
}
$oldStage=$env:GT_BEND_STAGE
try {
    if ($Broadleaf -and !$VerifyOnly) {
        if (Get-Process UnrealEditor*,blender,Wardogs* -ErrorAction SilentlyContinue) {throw 'Another renderer is active.'}
        $prepare=Join-Path $PSScriptRoot 'prepare_bend_crown.py'
        $app=Join-Path (Split-Path -Parent $EditorCmd) 'UnrealEditor.exe'
        $receipt=Join-Path $reportDir 'broadleaf-prepared.json'
        $started=[DateTime]::UtcNow
        $params=@(('"'+$project.FullName+'"'),'/Engine/Maps/Entry',('-ExecCmds="py '+$prepare.Replace('\','/')+'"'),
            '-Unattended','-NoSound','-NoSplash','-RenderOffScreen','-NoAutoSave',('-abslog="'+(Join-Path $reportDir 'broadleaf-prepare.log')+'"'))
        $job=Start-Process $app -ArgumentList $params -WindowStyle Hidden -PassThru -Wait
        if ($job.ExitCode -ne 0 -or !(Test-Path -LiteralPath $receipt) -or (Get-Item $receipt).LastWriteTimeUtc -lt $started) {throw 'No fresh broadleaf preparation receipt.'}
        $prepared=Get-Content -Raw -LiteralPath $receipt | ConvertFrom-Json
        if (!$prepared.ok) {throw $prepared.error}
    }
    $stages=if($VerifyOnly){@('verify')}else{@('build','verify')}
    if ($Broadleaf -and !$VerifyOnly) {$stages=@('broadleaf','verify')}
    foreach ($stage in $stages) {
        if (Get-Process UnrealEditor*,blender,Wardogs* -ErrorAction SilentlyContinue) {throw 'Another renderer is active.'}
        $env:GT_BEND_STAGE=$stage
        $marker=Join-Path $reportDir ($stage+'-session.json')
        $env:GT_BEND_RECEIPT=[guid]::NewGuid().ToString()
        $log=Join-Path $reportDir ($stage+'.log')
        $argsList=@(('"'+$project.FullName+'"'),'-run=pythonscript',('-script="'+$authoring+'"'),
            '-EnablePlugins=PythonScriptPlugin','-unattended','-nop4','-nosplash','-nosound',('-abslog="'+$log+'"'))
        $job=Start-Process -FilePath $EditorCmd -WorkingDirectory (Split-Path -Parent $EditorCmd) -ArgumentList $argsList -Wait -PassThru -WindowStyle Hidden
        if (($job.ExitCode -ne 0) -or !(Test-Path -LiteralPath $marker) -or
            ((Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).receipt -ne $env:GT_BEND_RECEIPT)) {
            throw "Unreal did not verify the $stage step. Check $reportDir."
        }
    }
} finally {
    $env:GT_BEND_STAGE=$oldStage
    Remove-Item Env:GT_BEND_RECEIPT -ErrorAction SilentlyContinue
}
Get-Content -LiteralPath (Join-Path $reportDir 'verified.json')
if ($Preview){Show-Bend}

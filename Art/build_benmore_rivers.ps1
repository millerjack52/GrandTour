param([double]$BakeSeconds=2480,[switch]$Resume,[switch]$ArtOnly,[switch]$Prepared)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
$python=Join-Path $projectRoot 'Saved/Tools/TerrainPython/Scripts/python.exe'
$blender='C:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$editor='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw 'Close Unreal before rebuilding the river assets.' }
if ($ArtOnly -and $Prepared) { throw 'Use either ArtOnly or Prepared.' }
Push-Location $projectRoot
try {
    if (-not $Prepared) {
    if (-not $ArtOnly) {
    $bakeArgs=@('Art/tools/bake_benmore_river.py','--seconds',$BakeSeconds)
    if ($Resume) {$bakeArgs+='--resume'}
    & $python @bakeArgs
    if ($LASTEXITCODE -ne 0) {throw 'River simulation or validation failed.'}
    & $python 'Art/tools/prepare_benmore_river_assets.py'
    if ($LASTEXITCODE -ne 0) {throw 'River mesh preparation failed.'}
    }
    & $python 'Art/tools/prepare_benmore_riverbank_art.py'
    if ($LASTEXITCODE -ne 0) {throw 'River bank art preparation failed.'}
    & $python 'Art/tools/prepare_benmore_river_mouth.py'
    if ($LASTEXITCODE -ne 0) {throw 'River mouth preparation failed.'}
    & $blender -b --python 'Art/Blender/export_benmore_river_mouth.py'
    if ($LASTEXITCODE -ne 0) {throw 'River mouth FBX export failed.'}
    if (-not $ArtOnly) {
        & $blender -b --python 'Art/Blender/export_benmore_rivers.py'
        if ($LASTEXITCODE -ne 0) {throw 'River FBX export failed.'}
    }
    }
    & $python 'Art/tools/validate_benmore_river_geometry.py'
    if ($LASTEXITCODE -ne 0) {throw 'River geometry validation failed.'}
    if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw 'Another Unreal process started during preparation; import must wait.' }
    $riverScript=if ($ArtOnly) {'refine_benmore_riverbanks.py'} else {'setup_benmore_rivers.py'}
    $launchArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLookKuwahara=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$riverScript+'"'),('-abslog="'+$projectRoot+'/Saved/Logs/BenmoreRivers.log"'))
    $process=Start-Process -FilePath $editor -ArgumentList $launchArgs -WindowStyle Hidden -PassThru
    Write-Output ('River import/review started, PID '+$process.Id+'. Reports: Art/Export/BenmoreRivers')
} finally {Pop-Location}

$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
Set-Location $taskRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Close Unreal before this rebuild.'}
if(Test-Path Saved/LidarAuthoringQA/RS7/job.py){throw 'An authoring job is already queued; preserve it.'}
python Art/tools/build_forest_ground_maps.py
if($LASTEXITCODE -ne 0){throw 'Coverage build failed'}
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Art/Blender/build_forest_ground_stamps.py
if($LASTEXITCODE -ne 0){throw 'Detail mesh build failed'}
& "$PSScriptRoot/build_guarded.ps1"
if($LASTEXITCODE -ne 0){throw 'Engine build failed'}
@'
import forest_ground
forest_ground.install()
forest_ground.build_motion()
u.SystemLibrary.quit_editor()
'@ | Set-Content Saved/LidarAuthoringQA/RS7/job.py
& "$PSScriptRoot/preview_lidar_first_section.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal import failed'}
$result=Get-Content Saved/LidarAuthoringQA/RS7/job-result.json -Raw | ConvertFrom-Json
if(-not $result.ok){throw $result.error}

$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
Set-Location $taskRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Close Unreal before this rebuild.'}
if(Test-Path Saved/LidarAuthoringQA/RS7/job.py){throw 'An authoring job is already queued; preserve it.'}
python Art/tools/build_peat_moss_textures.py
if($LASTEXITCODE -ne 0){throw 'Texture build failed'}
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Art/Blender/build_peat_moss_floor.py
if($LASTEXITCODE -ne 0){throw 'Floor build failed'}
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Art/Blender/peat_moss_lods.py
if($LASTEXITCODE -ne 0){throw 'Distance mesh build failed'}
@'
import peat_moss_ground
peat_moss_ground.run()
u.SystemLibrary.quit_editor()
'@ | Set-Content Saved/LidarAuthoringQA/RS7/job.py
& "$PSScriptRoot/preview_lidar_first_section.ps1"
if($LASTEXITCODE -ne 0){throw 'Unreal import failed'}
$result=Get-Content Saved/LidarAuthoringQA/RS7/job-result.json -Raw | ConvertFrom-Json
if(-not $result.ok){throw $result.error}

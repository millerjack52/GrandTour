$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$survey=Get-Content "$taskRoot/Saved/LidarAuthoringQA/Atmosphere/survey.json" -Raw | ConvertFrom-Json
$backup=$survey.backup
$candidate=Join-Path $backup 'CandidateCanopy'
New-Item -ItemType Directory -Force -Path $candidate | Out-Null
$kit="$taskRoot/Content/GrandTour/ArtTests/LidarStudy/CanopyKit"
try {
 foreach($k in 0..3){Copy-Item "$kit/SM_Canopy_$k.uasset" "$candidate/SM_Canopy_$k.uasset";Copy-Item "$backup/CanopyKit/SM_Canopy_$k.uasset" "$kit/SM_Canopy_$k.uasset"}
 & "$PSScriptRoot/capture_lidar_first_section.ps1" -Label atmosphere-fog-only -ViewsPath "$taskRoot/Saved/LidarAuthoringQA/Atmosphere/cameras.json"
 if($LASTEXITCODE -ne 0){throw 'Fog isolation capture failed'}
} finally {
 foreach($k in 0..3){if(Test-Path "$candidate/SM_Canopy_$k.uasset"){Copy-Item "$candidate/SM_Canopy_$k.uasset" "$kit/SM_Canopy_$k.uasset"}}
}

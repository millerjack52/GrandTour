param([int]$SampleCount=72)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
Set-Location $taskRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$qa="$taskRoot/Saved/LidarAuthoringQA/ForestShaders"
$backup=Get-Content "$qa/backup.json" -Raw | ConvertFrom-Json
$candidate="$qa/FinalMaterials"
New-Item -ItemType Directory -Force -Path $candidate | Out-Null
$materials=0..3 | ForEach-Object {"M_FirFar_$_.uasset"}
foreach($name in $materials){Copy-Item -LiteralPath "$taskRoot/Content/GrandTour/ArtTests/LidarStudy/CanopyKit/$name" -Destination "$candidate/$name" -Force}
try {
 foreach($name in $materials){Copy-Item -LiteralPath "$($backup.folder)/Content/GrandTour/ArtTests/LidarStudy/CanopyKit/$name" -Destination "$taskRoot/Content/GrandTour/ArtTests/LidarStudy/CanopyKit/$name" -Force}
 & "$PSScriptRoot/capture_lidar_section_motion.ps1" -Label ForestShaderBefore -SampleCount $SampleCount -Sequence /Game/GrandTour/ArtTests/LidarStudy/FirstSection/PerceivedDetail/LS_PD_Forest -OutputDirectory "$taskRoot/Saved/FSB"
 if($LASTEXITCODE -ne 0){throw 'Before motion failed'}
} finally {
 foreach($name in $materials){Copy-Item -LiteralPath "$candidate/$name" -Destination "$taskRoot/Content/GrandTour/ArtTests/LidarStudy/CanopyKit/$name" -Force}
}
& "$PSScriptRoot/capture_lidar_section_motion.ps1" -Label ForestShaderAfter -SampleCount $SampleCount -Sequence /Game/GrandTour/ArtTests/LidarStudy/FirstSection/PerceivedDetail/LS_PD_Forest -OutputDirectory "$taskRoot/Saved/FSA"
if($LASTEXITCODE -ne 0){throw 'After motion failed'}

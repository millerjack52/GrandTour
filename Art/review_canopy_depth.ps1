$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
& Art/capture_lidar_first_section.ps1 -Label canopy-depth-after -ViewsPath Saved/LidarAuthoringQA/ValleyGround/cameras.json
if($LASTEXITCODE -ne 0){throw 'Still capture failed'}
& Art/capture_lidar_section_motion.ps1 -Label canopy-depth-valley -SampleCount 72 -Sequence /Game/GrandTour/ArtTests/LidarStudy/CanopyDepth/LS_CD_Valley -PosesPath Saved/LidarAuthoringQA/CanopyDepth/motion-sequences.json -OutputDirectory C:/GrandTour/Saved/CDMotion
if($LASTEXITCODE -ne 0){throw 'Valley motion capture failed'}

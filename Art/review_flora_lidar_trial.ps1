# Run only when GPU memory is available. Does not close any user application.
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
& ./Art/run_flora_drive.ps1 -Stage audit
python Art/tools/verify_flora_trial_soil.py
if($LASTEXITCODE -ne 0){throw 'Saved soil verification failed'}
& ./Art/run_flora_drive.ps1 -Stage check
Copy-Item -LiteralPath Art/Export/FloraDrive/check-report.json -Destination Art/Export/FloraDrive/functional-report.json -Force
Copy-Item -LiteralPath Art/Export/FloraDrive/check.log -Destination Art/Export/FloraDrive/functional.log -Force
& ./Art/run_flora_drive.ps1 -Stage capture
if(Test-Path Art/Export/FloraDrive/shadows-report.json){
 python Art/tools/review_flora_ground_shadows.py
 if($LASTEXITCODE -ne 0){throw 'Ground shadow comparison validation failed'}
}
python Art/tools/review_flora_lidar_rocks.py
if($LASTEXITCODE -ne 0){throw 'Comparison evidence validation failed'}
Write-Output 'Comparison ready for visual inspection: C:/GrandTour/Art/Export/FloraDrive/lidar-mud-rocks-review.html'

param([string]$Label='baseline-repeat')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false;$swapped=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 $backup=Get-Content "$taskRoot/Saved/LidarAuthoringQA/RS7/backup.json" -Raw | ConvertFrom-Json
 $map="$taskRoot/Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap"
 $candidate=Join-Path $backup.path 'Candidate-for-baseline-test.umap'
 $baseline=Join-Path $backup.path 'Baseline-with-cameras.umap'
 Copy-Item -LiteralPath $map -Destination $candidate
 $expected=(Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
 Copy-Item -LiteralPath $baseline -Destination $map;$swapped=$true
 & "$PSScriptRoot/capture_lidar_first_section.ps1" -Label $Label
} finally {
 if($swapped){Copy-Item -LiteralPath $candidate -Destination $map;if((Get-FileHash -LiteralPath $map -Algorithm SHA256).Hash -ne $expected){throw 'Candidate restoration hash mismatch'}}
 if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()
}

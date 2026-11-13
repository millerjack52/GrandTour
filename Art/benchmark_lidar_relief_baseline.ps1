$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false;$swapped=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 $qa="$taskRoot/Saved/LidarAuthoringQA/RS7Relief";$backup=(Get-Content "$qa/survey.json" -Raw | ConvertFrom-Json).backup
 $dest="$taskRoot/Content/GrandTour/ArtTests/LidarStudy/FirstSection/SM_RS7_BankSkin.uasset"
 $candidate="$backup/Final-BankSkin.uasset"
 Copy-Item -LiteralPath $dest -Destination $candidate;$expected=(Get-FileHash -LiteralPath $candidate).Hash
 $swapped=$true;Copy-Item -LiteralPath "$backup/SM_RS7_BankSkin.uasset" -Destination $dest
 & "$PSScriptRoot/capture_lidar_first_section.ps1" -Label relief-before
} finally {
 if($swapped){Copy-Item -LiteralPath $candidate -Destination $dest;if((Get-FileHash -LiteralPath $dest).Hash -ne $expected){throw 'Final relief mesh restore mismatch'}}
 if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()
}

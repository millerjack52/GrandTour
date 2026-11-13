# Matched baseline for a material-only update. Restore candidate even on failure.
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false;$swapped=@()
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal reserved'}
 $qa="$taskRoot/Saved/LidarAuthoringQA/RS7Ground"
 $backup=(Get-Content "$qa/backup.json" -Raw | ConvertFrom-Json).path
 $candidate="$backup/FinalMaterials";New-Item -ItemType Directory -Force $candidate | Out-Null
 $dest="$taskRoot/Content/GrandTour/ArtTests/LidarStudy/FirstSection"
 $hashes=@{}
 foreach($name in @('M_BankSurface','M_BankEarth')) {
  Copy-Item -LiteralPath "$dest/$name.uasset" -Destination "$candidate/$name.uasset"
  $hashes[$name]=(Get-FileHash -LiteralPath "$candidate/$name.uasset").Hash
  $swapped+=$name
  Copy-Item -LiteralPath "$backup/$name.uasset" -Destination "$dest/$name.uasset"
 }
 & "$PSScriptRoot/capture_lidar_first_section.ps1" -Label ground-before-run
} finally {
 foreach($name in $swapped){Copy-Item -LiteralPath "$candidate/$name.uasset" -Destination "$dest/$name.uasset";if((Get-FileHash -LiteralPath "$dest/$name.uasset").Hash -ne $hashes[$name]){throw "Material restore failed: $name"}}
 if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()
}

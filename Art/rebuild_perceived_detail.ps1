# Rebuilds the accepted prototype's assets. Does not reconstruct the world/stand layout.
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
if(-not (Test-Path "$taskRoot/Art/Export/LidarStudy/FirstSection/PerceivedDetail/accepted.json")){throw 'No accepted detail recipe'}
$backupDir=Join-Path $taskRoot ('Saved/LidarAuthoringBackups/PerceivedRebuild-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmss'))
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
foreach($name in @('M_BankSurface.uasset','SM_RS7_Cascade_0.uasset','PerceivedDetail')){
 Copy-Item -LiteralPath "$taskRoot/Content/GrandTour/ArtTests/LidarStudy/FirstSection/$name" -Destination $backupDir -Recurse
}
python "$PSScriptRoot/tools/bake_perceived_detail.py"
if($LASTEXITCODE -ne 0){throw 'Surface bake failed'}
foreach($script in @('build_perceived_detail_fern.py','build_perceived_tree_occlusion.py')){
 $process=Start-Process 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -ArgumentList '--background','--python',('"'+$PSScriptRoot+'/Blender/'+$script+'"') -WindowStyle Hidden -PassThru
 $null=$process.Handle;$process.WaitForExit()
 if($process.ExitCode -ne 0){throw "Bake failed: $script"}
}
$job=@'
import rebuild_perceived_detail as rebuild;rebuild.run()
import validate_perceived_detail as check;check.run()
u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
'@
Set-Content -LiteralPath "$taskRoot/Saved/LidarAuthoringQA/RS7/job.py" -Value $job
& "$PSScriptRoot/preview_lidar_first_section.ps1"

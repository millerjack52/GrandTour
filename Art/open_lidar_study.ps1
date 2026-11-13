param([switch]$Play,[switch]$OriginalQuality,[switch]$ShowFPS,[switch]$Paddock,[switch]$House)
$ErrorActionPreference='Stop'
if($Paddock -and -not $Play){throw '-Paddock requires -Play'}
if($House -and (-not $Play -or $Paddock)){throw '-House requires -Play and cannot combine with -Paddock'}
& "$PSScriptRoot/wait_unreal_free.ps1" -MaxMinutes 0
if($LASTEXITCODE -ne 0){throw 'Unreal is already open. Load /Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy there.'}
$taskRoot=Split-Path $PSScriptRoot
$taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-GTNoLoad','-GTLookKuwahara=0')
$taskArgs+=('-abslog="'+$taskRoot+'/Saved/Logs/LidarDrive.log"')
if($OriginalQuality){$taskArgs+='-GTLidarPerformance=0'}
$preset=Get-Content "$PSScriptRoot/lidar_performance.json" -Raw | ConvertFrom-Json
if($Play){$taskArgs+=@('-game','-windowed',('-ResX='+$preset.output_resolution[0]),('-ResY='+$preset.output_resolution[1]))}
$commands=@()
if(-not $OriginalQuality){$commands+=@($preset.commands)}
if($ShowFPS){$commands+='stat fps'}
if($Paddock){
 $poses=Get-Content "$PSScriptRoot/Export/LidarStudy/Place/gs3-poses.json" -Raw | ConvertFrom-Json
 $pose=$poses[0]
 $commands+='EnableCheats'
 $commands+=('BugItGo {0} {1} {2} 0 {3} 0' -f $pose.x,$pose.y,$pose.z,$pose.yaw)
}
if($House){
 $layout=Get-Content "$PSScriptRoot/Export/LidarStudy/Homestead/layout.json" -Raw | ConvertFrom-Json
 $survey=Get-Content "$PSScriptRoot/Export/LidarStudy/Homestead/ground-survey.json" -Raw | ConvertFrom-Json
 $angle=$survey.yaw*[Math]::PI/180
 $localX=$layout.bay_local_cm[0];if($survey.mirror_x){$localX=-$localX}
 $x=$survey.anchor_cm[0]+$localX*[Math]::Cos($angle)-$layout.bay_local_cm[1]*[Math]::Sin($angle)
 $y=$survey.anchor_cm[1]+$localX*[Math]::Sin($angle)+$layout.bay_local_cm[1]*[Math]::Cos($angle)
 $commands+='EnableCheats'
 $commands+=('BugItGo {0} {1} {2} 0 {3} 0' -f $x,$y,($layout.bay_height_cm+100),($survey.yaw-90))
}
if($commands.Count){$taskArgs+=('-ExecCmds="'+($commands -join ',')+'"')}
# These overrides apply to this launch only. OriginalQuality uses the project's original settings.
# Explicitly interactive editor/game requested by the launcher user.
Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs

$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$folder='Saved/LidarAuthoringQA/CanopyDepth/DebugBackup'
New-Item -ItemType Directory -Force $folder | Out-Null
$paths=@('Mature','Pole','Edge') | ForEach-Object {"Content/GrandTour/ArtTests/LidarStudy/CanopyDepth/$_/M_PD_TreeProxy.uasset"}
for($i=0;$i -lt 3;$i++){Copy-Item -LiteralPath $paths[$i] -Destination "$folder/$i.uasset"}
try {
 $launch=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-abslog=C:/GrandTour/Saved/Logs/CanopyDepthDebug.log','-ExecutePythonScript=C:/GrandTour/Art/Unreal/debug_canopy_depth.py')
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();if($p.ExitCode -ne 0){throw 'Debug authoring failed'}
 & Art/capture_lidar_first_section.ps1 -Label canopy-depth-debug -ViewsPath Saved/LidarAuthoringQA/CanopyDepth/debug-camera.json
 if($LASTEXITCODE -ne 0){throw 'Debug capture failed'}
} finally {for($i=0;$i -lt 3;$i++){Copy-Item -LiteralPath "$folder/$i.uasset" -Destination $paths[$i] -Force}}

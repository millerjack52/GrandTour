$ferrariArgs = @(
    'C:/GrandTour/GrandTour.uproject', '-NullRHI', '-Unattended', '-NoSplash', '-NoSound', '-NoP4', '-GTNoLoad',
    '-ini:Engine:[CoreRedirects]:+PackageRedirects=(OldName=/Game/GrandTour/Demo/BenmoreFullSite/Layers/LI_Dirt,NewName=/Game/GrandTour/Demo/BenmoreRoads/Gaea/FirmGroundLayers/LI_Dirt)',
    '-ini:Engine:[CoreRedirects]:+PackageRedirects=(OldName=/Game/GrandTour/Demo/BenmoreFullSite/Layers/LI_Scrub,NewName=/Game/GrandTour/Demo/BenmoreRoads/Gaea/FirmGroundLayers/LI_Scrub)',
    '-ExecutePythonScript=C:/GrandTour/Art/Unreal/fix_benmore_firm_ground.py',
    '-abslog=C:/GrandTour/Saved/Logs/FerrariFirmGroundFix6.log'
)
$ferrariProcess = Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $ferrariArgs -WindowStyle Hidden -PassThru
$ferrariProcess.Id

$ErrorActionPreference='Stop'
if (Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6 -ErrorAction SilentlyContinue) { throw 'An editor or game is running' }
$root=Split-Path $PSScriptRoot
$editor='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'/Game/GrandTour/ArtTests/RoadBenchmark/L_RoadBenchmark','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-NoVSync',('-ExecutePythonScript="'+$root+'\Art\Unreal\capture_road_benchmark.py"'),('-abslog="'+$root+'\Saved\Logs\capture_road_benchmark.log"'))
$p=Start-Process -FilePath $editor -ArgumentList $argsList -WindowStyle Hidden -PassThru
Write-Output ('ROAD_CAPTURE_PID '+$p.Id)
$p.WaitForExit()
Write-Output ('ROAD_CAPTURE_EXIT '+$p.ExitCode)
exit $p.ExitCode

$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if (Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6 -ErrorAction SilentlyContinue) { throw 'An editor or game is running' }
$editor='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$log="$root\Saved\Logs\ground_material_smoke.log"
# Existing stationary test copy shares the newly imported mesh/material packages.
# This is a compilation/runtime smoke check, not an A/B performance measurement.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'/Game/GrandTour/ArtTests/RoadFordStyle/L_GrassPerf_On','-game','-RenderOffScreen','-dx12','-unattended','-nosplash','-nosound','-GTNoLoad','-NoVSync','-ResX=1440','-ResY=900','-ForceRes','-windowed','-csvGpuStats','-csvCaptureFrames=600','-ExitAfterCsvProfiling','-csvCompression=0','-GTLookKuwahara=0','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-abslog="'+$log+'"'))
$proc=Start-Process -FilePath $editor -ArgumentList $argsList -WindowStyle Hidden -PassThru
$proc.WaitForExit()
if ($proc.ExitCode -ne 0) { throw "Unreal exited $($proc.ExitCode)" }
if (Select-String -Path $log -Pattern 'Failed to compile Material|LogMaterial: Error|Fatal error') { throw 'Shader/runtime error; inspect log' }
Write-Output 'GROUND_SMOKE_OK'

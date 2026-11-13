param([switch]$VoxelDebug)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\capture_dense_tussock.py"'),('-abslog="'+$root+'\Saved\Logs\dense_tussock_capture.log"'))
if($VoxelDebug){$argsList+='-DTDenseDebug'}
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$reportFile=if($VoxelDebug){'voxel-debug-report.json'}else{'capture-report.json'}
$report=Get-Content "$root\Art\Export\DenseTussock\$reportFile" -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'DENSE_CAPTURE_OK'

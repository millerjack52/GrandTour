$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if (Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6 -ErrorAction SilentlyContinue) { throw 'An editor or game is running' }
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-NoLoadStartupPackages',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_dense_tussock.py"'),('-abslog="'+$root+'\Saved\Logs\dense_tussock_setup.log"'))
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$report=Get-Content "$root\Art\Export\DenseTussock\unreal-setup-report.json" -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'DENSE_TUSSOCK_SETUP_OK'

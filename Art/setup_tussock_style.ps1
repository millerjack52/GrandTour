$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-NoLoadStartupPackages','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_tussock_style.py"'),('-abslog="'+$root+'\Saved\Logs\tussock_style_setup.log"'))
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$report=Get-Content "$root\Art\Export\TussockStyle\setup-report.json" -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'TUSSOCK_STYLE_SETUP_OK'

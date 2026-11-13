$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_live_mud_drive.py"'),('-abslog="'+$root+'\Saved\Logs\live_mud_setup.log"'))
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\LiveMudDrive\setup-report.json"
if($p.ExitCode -ne 0 -or $file.LastWriteTime -lt $started){throw 'Import process failed or report is stale'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'LIVE_MUD_SETUP_OK'

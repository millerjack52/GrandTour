# Wheel spray P2 item 7 (docs/WHEEL_SPRAY_PLAN.md): the spray's six pictures, mid-action, with the live counts per emitter
# (Art/Unreal/check_wheel_spray.py). A full editor with -RenderOffScreen; refuses with an editor open. A game may be open.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is already running; close it before this run.'}
$started=Get-Date
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md): a fixed 1/60 s step; the script renders only for its captures.
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-UseFixedTimeStep','-FPS=60','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLookKuwahara=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/check_wheel_spray.py"'),('-abslog="'+$root+'/Saved/Logs/wheel_spray_check.log"'))
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
$file=Get-Item -LiteralPath ($root+'/Art/Export/WheelSpray/check-report.json') -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw 'No fresh wheel spray report was written.'}
$report=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output ('WHEEL_SPRAY_CHECK_OK; editor exit '+$p.ExitCode)

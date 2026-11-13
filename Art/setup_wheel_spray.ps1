# Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md): the spray's textures, clumps, materials and NS_GT_WheelSpray, in a full editor with
# -RenderOffScreen (the sprite materials and the Niagara GPU scripts compile for real). Refuses with an editor open.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is already running; close it before this run.'}
# The system is rebuilt from nothing each run: its old file goes before the editor starts. Built over an existing package (an
# in-session delete leaves the file), the saved system crashed every later load (2026-10-10).
Remove-Item -LiteralPath ($root+'/Content/GrandTour/FX/NS_GT_WheelSpray.uasset') -ErrorAction SilentlyContinue
$started=Get-Date
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_wheel_spray.py"'),('-abslog="'+$root+'\Saved\Logs\wheel_spray_setup.log"'))
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
$file=Get-Item "$root\Art\Export\WheelSpray\setup-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw 'No fresh setup report was written.'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw ('Wheel spray setup failed: '+$report.error+' '+(($report.niagara_log|Select-String 'FAIL') -join ' '))}
Write-Output ('WHEEL_SPRAY_SETUP_OK; editor exit '+$p.ExitCode)

$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Another Unreal editor is running; export must wait.'}
$started=Get-Date
$launchArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 20"',('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/export_benmore_gaea.py"'),('-abslog="'+$projectRoot+'/Saved/Logs/BenmoreGaeaExport.log"'))
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launchArgs -WindowStyle Hidden -Wait -PassThru
$report=Get-Item -LiteralPath ($projectRoot+'/Art/Export/BenmoreGaea/source/unreal-export-report.json') -ErrorAction SilentlyContinue
if(-not $report -or $report.LastWriteTime -lt $started){throw 'No fresh Gaea export report.'}
$result=Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json
if(-not $result.ok){throw $result.error}
Write-Output ('BENMORE_GAEA_EXPORT_OK; editor exit '+$p.ExitCode)

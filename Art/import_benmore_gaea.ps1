param([switch]$ReviewOnly,[switch]$FinishPreview)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Another Unreal editor is running. Wait for it to finish before this import.'}
if(Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object {$_.CommandLine -like '*Art/suite.sh*'}){throw 'The shared Unreal suite is still running between tests. Wait for the whole suite to finish.'}
$scriptName=if($ReviewOnly){'check_benmore_gaea_review.py'}elseif($FinishPreview){'finish_benmore_gaea_preview.py'}else{'import_benmore_gaea.py'}
$reportName=if($ReviewOnly -or $FinishPreview){'unreal-review-report.json'}else{'unreal-import-report.json'}
$logName=if($ReviewOnly){'BenmoreGaeaReview.log'}elseif($FinishPreview){'BenmoreGaeaFinish.log'}else{'BenmoreGaeaImport.log'}
$started=Get-Date
$launchArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLookKuwahara=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),('-abslog="'+$projectRoot+'/Saved/Logs/'+$logName+'"'))
$editor=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launchArgs -WindowStyle Hidden -PassThru
$editor.WaitForExit()
$report=Get-Item -LiteralPath ($projectRoot+'/Art/Export/BenmoreGaea/integration/'+$reportName) -ErrorAction SilentlyContinue
if(-not $report -or $report.LastWriteTime -lt $started){throw 'No fresh Gaea import/review report.'}
$result=Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json
if(-not $result.ok){throw $result.error}
Write-Output ('BENMORE_GAEA_OK; editor exit '+$editor.ExitCode)

param([ValidateSet('Setup','Check')][string]$Mode='Setup',[switch]$AllowGame)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is already running; close it before this run.'}
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md): the check steps a fixed 1/60 s and renders only for its pictures, so
# -AllowGame runs it with a game open.
if($Mode -eq 'Check' -and -not $AllowGame -and (Get-Process GrandTour,GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue)){throw 'A game is running (-AllowGame runs anyway).'}
$scriptName=if($Mode -eq 'Setup'){'setup_deformable_gravel.py'}else{'check_deformable_gravel.py'}
$reportName=if($Mode -eq 'Setup'){'setup-report.json'}else{'drive-report.json'}
$runStarted=Get-Date
$launchArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLookKuwahara=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900',$(if($Mode -eq 'Check'){'-UseFixedTimeStep'}else{'-NoFixedStep'}),$(if($Mode -eq 'Check'){'-FPS=60'}else{'-NoFPS'}),$(if($Mode -eq 'Check'){'-ExecCmds="t.MaxFPS 0"'}else{'-ExecCmds="t.MaxFPS 30"'}),('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$scriptName+'"'),('-abslog="'+$projectRoot+'/Saved/Logs/DeformableGravel'+$Mode+'.log"'))
$process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launchArgs -WindowStyle Hidden -Wait -PassThru
$reportFile=Get-Item -LiteralPath ($projectRoot+'/Art/Export/DeformableGravel/'+$reportName) -ErrorAction SilentlyContinue
if(-not $reportFile -or $reportFile.LastWriteTime -lt $runStarted){throw 'No fresh gravel report was written.'}
$report=Get-Content -LiteralPath $reportFile.FullName -Raw | ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output ('GRAVEL_'+$Mode.ToUpper()+'_OK; editor exit '+$process.ExitCode+'; '+$reportFile.FullName)

param([string]$Stage='B1c',[string]$Only='')   # -Only Verge (or Gravel_Chase,Gravel_Close,...): a subset
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Benmore integration B1b / B1c (docs/BENMORE_INTEGRATION_PLAN.md): the spray's three pictures on L_Benmore_GaeaReview, one editor run
# (Art/Unreal/capture_benmore_b1b.py): -RenderOffScreen, a fixed 1/60 s step, Play In Editor in a 1440 x 900 window. Saves nothing.
# Call Art/wait_unreal_free.ps1 first, as its own command. A game may be open (the run does not check for one).   -> Art/Export/Benmore<Stage>
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is running (run Art/wait_unreal_free.ps1 first)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-UseFixedTimeStep','-FPS=60','-dx12','-Unattended','-NoSplash','-NoSound','-nop4',
    '-GTNoLoad','-GTLookKuwahara=0','-ResX=1440','-ResY=900',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
    '-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\capture_benmore_b1b.py"'),('-abslog="'+$root+'\Saved\Logs\benmore_'+$Stage.ToLower()+'.log"'))
$env:GT_BENMORE_STAGE=$Stage
$env:GT_BENMORE_ONLY=$Only
$name=if($Only){'capture_'+($Only -replace ',','_')+'.json'}else{'capture.json'}
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\Benmore$Stage\$name" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output ("BENMORE_{1}_CAPTURE_OK {0}" -f $file.FullName,$Stage.ToUpper())

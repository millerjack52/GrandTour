param([ValidateSet('inspect','apply','check')][string]$Step='inspect')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Benmore integration B1 (docs/BENMORE_INTEGRATION_PLAN.md B1): one editor run per step, -RenderOffScreen (shader counts need HLSL, the
# landscape's physical material and grass maps render, the pictures render). Call Art/wait_unreal_free.ps1 first, as its own command.
# A game may be open (the run does not check for one).
#   inspect   Art/Unreal/inspect_benmore_b1.py: the read-only inventory                                    -> inventory.json
#   apply     Art/Unreal/benmore_gt_ground.py: MPC, MF_GT_GroundDetail, the review material, grass types,
#             physical materials; saves the review map                                                     -> apply-report.json
#   check     Art/Unreal/benmore_gt_ground_check.py: shader counts, the surface traces, BI_* pictures and the
#             scatter's instance counts at three review locations (saves nothing)                          -> check.json
$map=@{inspect=@('inspect_benmore_b1.py','inventory.json');apply=@('benmore_gt_ground.py','apply-report.json');check=@('benmore_gt_ground_check.py','check.json')}
$script,$out=$map[$Step]
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is running (run Art/wait_unreal_free.ps1 first)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ResX=1440','-ResY=900',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
    '-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\'+$script+'"'),('-abslog="'+$root+'\Saved\Logs\benmore_b1_'+$Step+'.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\BenmoreB1\$out" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output ("BENMORE_B1_{0}_OK {1}" -f $Step.ToUpper(),$file.FullName)

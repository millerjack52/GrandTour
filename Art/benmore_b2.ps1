param([ValidateSet('strips','setup','capture','triage')][string]$Step='strips',[string]$Tag='after')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Benmore integration B2 (docs/BENMORE_INTEGRATION_PLAN.md B2 and its addendum): one editor run per step, -RenderOffScreen.
# Call Art/wait_unreal_free.ps1 first, as its own command. A game may be open (the run does not check for one).
#   strips   Art/Unreal/relief_pictures.py on L_MudVariants alone (GT_RELIEF_STRIPS=MudVariants): Relief_OnFoot copied to
#            Art/Export/BenmoreB2/Strips/Relief_OnFoot_<Tag>.png (-Tag ref before B2a, after once built)  -> pictures-b2<tag>.json
#   setup    Art/Unreal/setup_benmore_b2.py (-Tag a: B2a's materials; -Tag b: B2b's zones and the map): the deform zones placed in L_Benmore_GaeaReview from Art/Export/BenmoreB2/plan.json,
#            M_GC_Terrain's coverage hole and apron, M_GT_Gravel's tint                                    -> BenmoreB2/setup.json
#   capture  Art/Unreal/capture_benmore_b2.py: the B2b pictures (PIE, a fixed 1/60 s step; -Tag edge,gravel takes those alone)                   -> BenmoreB2/capture.json
#            (-Tag triage: the B2 cameras and the Terrace loop join on foot after the triage                          -> BenmoreTriage/capture.json)
#   triage   Art/Unreal/benmore_triage.py: the deform zones out of L_Benmore_GaeaReview, M_GC_Terrain to the surface types alone -> BenmoreTriage/triage.json
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is running (run Art/wait_unreal_free.ps1 first)'}
$out="$root\Art\Export\BenmoreB2"
New-Item -ItemType Directory -Force "$out\Strips" | Out-Null
$common=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False')
switch($Step){
  'strips'  {$env:GT_RELIEF_TAG="b2$Tag";$env:GT_RELIEF_STRIPS='MudVariants';$env:GT_RELIEF_GR2='';$env:GT_RELIEF_CAMERAS=''
             $script='relief_pictures.py';$report="$root\Art\Export\GroundRelief\pictures-b2$Tag.json";$extra=@('-ExecCmds="t.MaxFPS 30"')}
  'setup'   {$env:GT_B2_STAGE=$Tag;$script='setup_benmore_b2.py';$report="$out\setup.json";$extra=@()}
  'triage'  {$script='benmore_triage.py';$report="$root\Art\Export\BenmoreTriage\triage.json";$extra=@()}
  'capture' {$env:GT_B2_ONLY=$(if($Tag -ne 'after'){$Tag}else{''});$script='capture_benmore_b2.py'
             $report=$(if($Tag -eq 'triage'){"$root\Art\Export\BenmoreTriage\capture.json"}elseif($env:GT_B2_ONLY){"$out\capture_"+($env:GT_B2_ONLY -replace ',','_')+'.json'}else{"$out\capture.json"})
             $extra=@('-UseFixedTimeStep','-FPS=60','-GTNoLoad','-GTLookKuwahara=0','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 30"')}
}
$argsList=$common+$extra+@(('-ExecutePythonScript="'+$root+'\Art\Unreal\'+$script+'"'),('-abslog="'+$root+'\Saved\Logs\benmore_b2_'+$Step+'.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item $report -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No report written by this run (editor exit $($p.ExitCode))"}
$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $r.ok){throw $r.error}
if($Step -eq 'strips'){Copy-Item "$root\Art\Export\MudVariants\Relief_OnFoot.png" "$out\Strips\Relief_OnFoot_$Tag.png" -Force}
Write-Output ("BENMORE_B2_{0}_OK {1}" -f $Step.ToUpper(),$file.FullName)

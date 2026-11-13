param([ValidateSet('import','stats','pictures')][string]$Step='stats',[string]$Tag='after')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Ground relief GR2 phase B (docs/GROUND_RELIEF_PLAN.md GR2): one editor run per step, -RenderOffScreen (shader stats need HLSL; the
# pictures render). Call Art/wait_unreal_free.ps1 first, as its own command. A game may be open (the run does not check for one).
#   import    Art/Unreal/import_ground_detail.py: TA_GD_{Color,Normal,ORH}, SM_GD_*, M_GT_GroundScatter     -> import-report.json
#   stats     Art/Unreal/ground_detail_stats.py (-Tag baseline|after)                                     -> shader-stats-<tag>.json
#   pictures  Art/Unreal/relief_pictures.py, GR1c's cameras + Ground_Close/_Detail0/Far (GT_RELIEF_GR2)       -> GroundRelief/pictures-gr2.json
$map=@{import=@('import_ground_detail.py','import-report.json');stats=@('ground_detail_stats.py',"shader-stats-$Tag.json");pictures=@('relief_pictures.py','..\GroundRelief\pictures-gr2.json')}
$script,$out=$map[$Step]
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is running (run Art/wait_unreal_free.ps1 first)'}
$env:GT_GD_TAG=$Tag
if($Step -eq 'pictures'){$env:GT_RELIEF_TAG='gr2';$env:GT_RELIEF_GR2='1';$env:GT_RELIEF_CAMERAS="$root\Art\Export\GroundRelief\pictures-gr1c.json"}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\'+$script+'"'),('-abslog="'+$root+'\Saved\Logs\ground_detail_'+$Step+'.log"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item "$root\Art\Export\GroundDetailGR2\$out" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No report written by this run (editor exit $($p.ExitCode))"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
if($Step -eq 'stats'){foreach($r in $report.rows){Write-Output ("{0} {1} [{2}]: pixel {3}, vertex {4}, samplers {5}, pixel texture samples {6}" -f $r.role,$r.material,$r.ground_detail,$r.pixel_instructions,$r.vertex_instructions,$r.samplers,$r.pixel_texture_samples)}}
Write-Output ("GROUND_DETAIL_{0}_OK {1}" -f $Step.ToUpper(),$file.FullName)

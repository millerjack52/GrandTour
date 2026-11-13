param([ValidateSet('before','mw1','after','diag','mrd')][string]$Tag='after',[string]$Cameras='',[int]$PoolSize=0)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md items 1, 4, 5): Art/Unreal/check_mud_water.py on L_MudVariants (the owner's
# on-foot frame, its debug set, the moving water, the rings drive, the footsteps, the close mud and the buffer dumps), then
# Art/sample_mud_water.py (the diagnosis diffs, the motion, glare and PBR gates). -Tag before is the diagnosis run before any
# change; -Cameras <check-before.json> reuses that run's puddle and frames. No cost or timing measurement.
# Run Art/wait_unreal_free.ps1 first (an editor still refuses here). A running game is named, never closed, and the run goes on
# (docs/CHECKS_UNDER_GAME_PLAN.md: a fixed 1/60 s step, the scene rendered only for the pictures).
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'An editor is running (Art/wait_unreal_free.ps1 first)'}
$games=@(Get-Process GoWR,GoW,FarCry6,Ace7Game -ErrorAction SilentlyContinue)
if($games.Count){Write-Output ('A game is running: '+(($games|ForEach-Object{$_.Name})-join ', ')+'; the check runs anyway')}
$env:GT_MW_TAG=$Tag
$env:GT_MW_CAMERAS=$Cameras
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-UseFixedTimeStep','-FPS=60','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900',('-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100'+$(if($PoolSize -gt 0){",r.Streaming.PoolSize $PoolSize"}else{''})+'"'),('-ExecutePythonScript="'+$root+'\Art\Unreal\check_mud_water.py"'),('-abslog="'+$root+'\Saved\Logs\mud_water_check_'+$Tag+'.log"'))
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$code=$p.ExitCode
# Mud roads MRD1: -Tag mrd writes Art/Export/MudRoads/check-mrd.json and Art/sample_mud_roads.py reads it.
$dir=$(if($Tag -eq 'mrd'){'MudRoads'}else{'MudWater'})
$file=Get-Item "$root\Art\Export\$dir\check-$Tag.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No check report written by this run (editor exit $code)"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if($code -eq -1073741819){Write-Output 'Editor exit -1073741819 after the report: the known shutdown fault (LM0)'}elseif($code -ne 0){Write-Output "Editor exit $code after a fresh report"}
if($report.error){Write-Output ('CHECK ERROR: '+$report.error)}
Write-Output ("puddle: {0}" -f ($report.puddle|ConvertTo-Json -Compress))
Write-Output ("fixed step: {0}" -f ($report.check_run.fixed_dt|ConvertTo-Json -Compress))
Write-Output ("pipeline (tooling only): {0}" -f ($report.check_run.pipeline|ConvertTo-Json -Compress))
foreach($s in $report.steps){Write-Output "step: $s"}
if($Tag -eq 'mrd'){& python "$root\Art\sample_mud_roads.py" $file.FullName}else{& python "$root\Art\sample_mud_water.py" $file.FullName}
if(-not $report.ok){throw 'The check did not finish (report ok false)'}
Write-Output 'MUD_WATER_CHECK_OK'

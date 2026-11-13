param([switch]$AllowGame)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# MudRunner MR2 (docs/MUDRUNNER_LESSONS_PLAN.md MR2 item 7, docs/MUD_VARIANTS.md): the muddy car through L_MudDrive's ford -
# Car_PreFord.png at 74 m (after the mud) and Car_Washed.png at 109 m (after the ford), the body state before and after.
# Functional only: no cost or timing measurement (the owner tests performance). -AllowGame runs it with a game open (the owner's
# rule since 2026-10-08); an editor still refuses.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'An editor is running'}
if(-not $AllowGame -and (Get-Process FarCry6,GoW,GoWR -ErrorAction SilentlyContinue)){throw 'A game is running (GoWR, GoW and FarCry6 are checked; -AllowGame runs anyway)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-ExecutePythonScript="'+$root+'\Art\Unreal\check_car_washed.py"'),('-abslog="'+$root+'\Saved\Logs\car_washed.log"'))
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
$file=Get-Item "$root\Art\Export\LiveMudDrive\car-washed-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No report written by this run (editor exit $code)"}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if($code -eq -1073741819){Write-Output 'Editor exit -1073741819 (0xC0000005) after the report: the known shutdown fault (LM0), not a check failure'}
elseif($code -ne 0){Write-Output "Editor exit $code after a fresh report (not judged)"}
Write-Output ("viewport: $($report.viewport_size -join 'x') (play: $($report.play_mode)); weather $($report.weather); gt.Mud.CarMud $($report.car_mud)")
foreach($k in 'mud','ford'){$l=$report.$k;if($l){Write-Output ("{0} leg: reached {1}, end {2} m in {3} s, max sinkage {4} m, max water {5} m, {6} s in water over 5 cm" -f $k,$l.reached,$l.end_m,$l.s,$l.max_sink_m,$l.max_water_m,$l.water_over_5cm_s)}}
foreach($k in 'before_ford','after_ford'){$b=$report.$k;if($b){Write-Output ("{0}: {1}" -f $k,$b.describe);Write-Output ("  mud line {0} cm, coat line {1} cm, washed band {2} cm at {3}, MudWet {4}, tyres {5}; wheel bottoms Z {6}, wheel geometry {7}, tyre slots {8}; MR2b fans {9}" -f $b.mud_line_cm,$b.coat_line_cm,$b.wash_cm,$b.wash_amount,$b.mud_wet,($b.tyres -join ' / '),$b.mud_base_z,($b.wheel_geom -join ' / '),$b.tyre_slots,($b.fan_coat -join ' / '))}}
foreach($i in $report.images){Write-Output "picture: $i"}
# MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP item 4): the PBR validation rows from L_MudDrive's buffer dumps.
if($report.mrp){try{& python "$root\Art\sample_mud_pbr.py" "$root\Art\Export\LiveMudDrive\car-washed-report.json"}catch{Write-Output "MRP sampler did not run: $_"}}
if(-not $report.ok){throw "Car washed check failed (editor exit $code): $($report.error)"}
Write-Output 'CAR_WASHED_OK'

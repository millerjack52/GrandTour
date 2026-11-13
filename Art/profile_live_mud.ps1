param([string]$Tag='ref')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Living mud LM4e (docs/LIVING_MUD_PLAN.md LM4e): the clay reference for the snow's cost on L_MudDrive (Art/Unreal/profile_live_mud.py):
# the dry crossing's frame and the clay bog patch's own GPU cost from the view matching the snow profile's cost camera.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW,GoWR,blender -ErrorAction SilentlyContinue){throw 'Editor, Blender or a game is running (GoWR, GoW and FarCry6 are checked)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-csvGpuStats','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-ExecutePythonScript="'+$root+'\Art\Unreal\profile_live_mud.py"'),('-abslog="'+$root+'\Saved\Logs\profile_live_mud_'+$Tag+'.log"'))
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
$p.StartInfo.EnvironmentVariables['GT_MUD_PROFILE_TAG']=$Tag
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$code=$p.ExitCode
$file=Get-Item "$root\Art\Export\LiveMudDrive\Profile_$Tag\profile-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No mud profile report written by this run (editor exit $code)"}
$r=Get-Content $file.FullName -Raw|ConvertFrom-Json
if($r.error){Write-Output "ERROR: $($r.error)"}
$pt=$r.patch
Write-Output ("mud profile [{0}]: viewport {1}; bog patch section {2}, cell {3} cm, {4} cells, {5} triangles, box {6} - {7}; warm {8} s" -f $Tag,($r.viewport_size -join 'x'),$pt.section,$pt.cell_cm,($pt.cells -join 'x'),$pt.mesh_triangles,($pt.bounds_min -join ','),($pt.bounds_max -join ','),$r.warm_s)
$d=$r.dry;$c=$d.csv
Write-Output ("dry crossing: end {0} m in {1} s; frame {2} game {3} draw {4} gpu {5} (base {6} shadows {7} lights {8} post {9}); UI {10}; settle {11}/{12} upload {13}/{14} stamp {15}/{16} clods {17}/{18} ms" -f $d.end_x_m,$d.elapsed_s,$c.FrameTime,$c.GameThreadTime,$c.render_busy_ms,$c.GPUTime,$c.base,$c.shadows,$c.lights,$c.post,$c.'Exclusive/GameThread/UI',$d.settle_mean_ms,$d.settle_p99_ms,$d.upload_mean_ms,$d.upload_p99_ms,$d.stamp_mean_ms,$d.stamp_p99_ms,$d.clod_mean_ms,$d.clod_p99_ms)
foreach($view in @('cost','match')){$pc=$r.('patch_cost_'+$view)
if($pc){foreach($k in @('visible','hidden','visible_minus_hidden')){$v=$pc.$k;Write-Output ("patch [{10}] {0}: frame {1} game {2} gpu {3} base {4} shadows {5} lights {6} lumen {7} translucency {11} post {8} velocity {9}" -f $k,$v.FrameTime,$v.GameThreadTime,$v.GPUTime,$v.base,$v.shadows,$v.lights,$v.lumen,$v.post,$v.velocity,$view,$v.translucency)}}}
if(-not $r.ok){throw "Mud profile failed (editor exit $code)"}

param([string]$Tag='before',[string]$Sections='warm,drive,replay,pics,stand,toggles',[string]$Switches='',[string]$PassSwitches='',[string]$StandOnly='')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Living mud LM4e (docs/LIVING_MUD_PLAN.md LM4e, docs/LIVE_SNOW_DRIVE.md): the snow's cost in one Play In Editor session on
# L_SnowDrive (Art/Unreal/profile_live_snow.py), with the snow check's window, flags and CSV GPU stats. -Tag names the run
# (before, cut1, after ...), -Sections picks the parts (warm, drive, replay, pics, stand, toggles), -Switches adds LM4e
# switches to the standing ABBA set, -PassSwitches to the pass-1 set, -StandOnly replaces the standing set.
# Refuses with a game, Blender or any Unreal running: the timings would be someone else's.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,FarCry6,GoW,GoWR,blender -ErrorAction SilentlyContinue){throw 'Editor, Blender or a game is running (GoWR, GoW and FarCry6 are checked)'}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-csvGpuStats','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-ExecutePythonScript="'+$root+'\Art\Unreal\profile_live_snow.py"'),('-abslog="'+$root+'\Saved\Logs\profile_live_snow_'+$Tag+'.log"'))
$started=Get-Date
$p=[Diagnostics.Process]::new()
$p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$p.StartInfo.Arguments=$argsList -join ' '
$p.StartInfo.UseShellExecute=$false
$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
$p.StartInfo.EnvironmentVariables['GT_SNOW_PROFILE_TAG']=$Tag
$p.StartInfo.EnvironmentVariables['GT_SNOW_PROFILE']=$Sections
$p.StartInfo.EnvironmentVariables['GT_SNOW_PROFILE_SWITCHES']=$Switches
$p.StartInfo.EnvironmentVariables['GT_SNOW_PROFILE_PASS_SWITCHES']=$PassSwitches
$p.StartInfo.EnvironmentVariables['GT_SNOW_PROFILE_STAND_ONLY']=$StandOnly
if(-not $p.Start()){throw 'Unreal did not start'}
$p.WaitForExit()
$code=$p.ExitCode
$file=Get-Item "$root\Art\Export\LiveSnowDrive\Profile_$Tag\profile-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw "No profile report written by this run (editor exit $code)"}
if($code -eq -1073741819){Write-Output 'Editor exit -1073741819 (0xC0000005) after the report: the known shutdown fault (LM0)'}
elseif($code -ne 0){Write-Output "Editor exit $code after the report (not judged)"}
& python "$root\Art\tools\summarise_snow_profile.py" $file.FullName
if($LASTEXITCODE -ne 0){throw 'The profile summary failed'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $report.ok){throw "Snow profile failed (editor exit $code): $($report.error)"}

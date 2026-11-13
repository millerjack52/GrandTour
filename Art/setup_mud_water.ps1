# Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md): M_GT_Mud, M_GT_MudWater, MPC_TrackPaint's two switches and the water rings
# (T_GT_WaterRings, M_GT_WaterRing, NS_GT_WaterRings) - Art/Unreal/setup_mud_water.py in a full editor with -RenderOffScreen (the
# materials and the Niagara script compile for real). The ring atlas comes first from headless Blender
# (Art/Blender/build_water_rings.py). Run Art/wait_unreal_free.ps1 first; an editor still refuses here.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is already running (Art/wait_unreal_free.ps1 first)'}
$games=@(Get-Process GoWR,GoW,FarCry6,Ace7Game -ErrorAction SilentlyContinue)
if($games.Count){Write-Output ('A game is running: '+(($games|ForEach-Object{$_.Name})-join ', ')+'; the setup runs anyway')}
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup --python "$root/Art/Blender/build_water_rings.py" | Select-String 'WATER_RINGS_ATLAS_OK|Error' | ForEach-Object { $_.Line.Substring(0,[Math]::Min(200,$_.Line.Length)) }
if(-not (Test-Path "$root/Art/Export/MudWater/T_GT_WaterRings.png")){throw 'No ring atlas'}
# The system is rebuilt from nothing each run: its old file goes before the editor starts (WHEEL_SPRAY 2026-10-10).
Remove-Item -LiteralPath ($root+'/Content/GrandTour/FX/NS_GT_WaterRings.uasset') -ErrorAction SilentlyContinue
$started=Get-Date
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_mud_water.py"'),('-abslog="'+$root+'\Saved\Logs\mud_water_setup.log"'))
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
$file=Get-Item "$root\Art\Export\MudWater\setup-report.json" -ErrorAction SilentlyContinue
if(-not $file -or $file.LastWriteTime -lt $started){throw 'No fresh setup report was written.'}
$report=Get-Content $file.FullName -Raw|ConvertFrom-Json
foreach($t in 'before','after'){foreach($r in $report.("shader_stats_$t")){Write-Output ("shader stats {0} {1}: pixel {2} instructions, vertex {3}, samplers {4}, pixel texture samples {5}" -f $t,$r.material,$r.pixel_instructions,$r.vertex_instructions,$r.samplers,$r.pixel_texture_samples)}}
$report.niagara_log | Where-Object { $_ -match 'FAIL|compiled|module|BUILD|off$' } | ForEach-Object { Write-Output "niagara: $_" }
if(-not $report.ok){throw ('Mud water setup failed: '+$report.error)}
Write-Output ('MUD_WATER_SETUP_OK; editor exit '+$p.ExitCode)

param([ValidateSet('Install','Check','RoadRelief','Density','ClodCorrection','RoadConditions','LivingRoads','MudPush','StartBog')][string]$Mode='Check',[switch]$NoVisual)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
 if(-not $acquired){throw 'Unreal slot is reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Editor is already running'}
 $script=if($Mode -eq 'StartBog'){'add_start_bog.py'}elseif($Mode -eq 'Install'){'install_procedural_ground.py'}elseif($Mode -eq 'RoadRelief'){'check_road_relief.py'}elseif($Mode -eq 'Density'){'check_ground_density.py'}elseif($Mode -eq 'ClodCorrection'){'correct_road_clods.py'}elseif($Mode -in @('RoadConditions','LivingRoads','MudPush')){'check_road_conditions.py'}else{'check_procedural_ground.py'}
 $taskArgs=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/ProceduralGround-'+$Mode+'.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"'))
 if($Mode -in @('LivingRoads','MudPush')){$taskArgs+='-GTLivingRoads'}; if($Mode -eq 'MudPush'){$taskArgs+='-GTMudPush'}
 if($NoVisual -or $Mode -eq 'ClodCorrection'){if($Mode -notin @('Density','ClodCorrection','RoadConditions','LivingRoads','MudPush','StartBog')){throw 'NoVisual is not supported for this mode'};$NoVisual=$true;if($Mode -ne 'StartBog'){$taskArgs=@($taskArgs|Where-Object {$_ -notin @('-RenderOffScreen','-dx12')});$taskArgs+='-NullRHI'};$taskArgs+='-GTDensityNoVisual'}
 $reportName=if($NoVisual){$Mode.ToLower()+'-functional'}else{$Mode.ToLower()}
 $started=Get-Date
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
 $ownedProcessHandle=$p.Handle
 while(-not $p.WaitForExit(5000)){if(((Get-Date)-$started).TotalSeconds -gt 1200){Stop-Process -Id $p.Id;throw 'Owned authoring check exceeded timeout'}}
 $p.WaitForExit();$exitStatus=$p.ExitCode
 $f=Get-Item "$taskRoot/Art/Export/ProceduralGround/$reportName.json";$r=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json
 @{mode=$Mode;no_visual=[bool]$NoVisual;exit_code=$exitStatus;started=$started.ToString('o');report_written=$f.LastWriteTime.ToString('o');report_ok=$r.ok;process_id=$p.Id}|ConvertTo-Json|Set-Content "$taskRoot/Art/Export/ProceduralGround/$reportName-process.json"
 if($null -eq $exitStatus -or $exitStatus -ne 0 -or -not $r.ok -or $f.LastWriteTime -lt $started){throw "ProceduralGround $Mode failed; inspect report and process status"}
 if((Get-Content "$taskRoot/Saved/Logs/ProceduralGround-$Mode.log" -Raw) -match 'Failed to compile Material'){throw 'Material compilation failed'}
 if($Mode -in @('RoadConditions','LivingRoads','MudPush','StartBog') -and (Get-Content "$taskRoot/Saved/Logs/ProceduralGround-$Mode.log" -Raw) -match 'Ensure condition failed:|Fatal error:'){throw 'Road-condition check logged an engine ensure or fatal error'}
 Write-Output "ProceduralGround $Mode passed"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

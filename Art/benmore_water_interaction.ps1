param([ValidateSet('Install','Review','Tests')][string]$Mode='Review',[switch]$WaitForShared,[switch]$WaveFinish)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if($WaitForShared){while(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){Start-Sleep -Seconds 3}}
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Shared Unreal is occupied; wait for its owner'}
$base=@(('"'+$root+'/GrandTour.uproject"'),'-Unattended','-NoSplash','-NoSound','-NoP4','-GTNoLoad')
if($Mode -eq 'Tests'){
    $log=Join-Path $root 'Saved/Logs/water_interaction_test.log'
    $argsList=$base+@('-NullRHI','-ExecCmds="Automation RunTests GrandTour.Water.RiverReference+GrandTour.Water.MovingDomain+GrandTour.Water.PassiveDetail+GrandTour.Water.InteractionVisuals"','-TestExit="Automation Test Queue Empty"',('-abslog="'+$log+'"'))
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
}else{
    $script=if($Mode -eq 'Install'){'install_benmore_water_interaction.py'}else{'check_benmore_water_interaction.py'}
    $argsList=$base+@('-RenderOffScreen','-dx12','-GTMorphology','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$root+'/Saved/Logs/BenmoreInteraction'+$Mode+'.log"'))
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
}
$started=Get-Date
if($WaveFinish){$argsList+=@('-GTWaveFinish')}
$p=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
if($Mode -eq 'Tests'){
    if((Get-Item $log).LastWriteTime -lt $started){throw 'Stale test log'}
    $rows=@(Select-String -LiteralPath $log -Pattern 'Test Completed\. Result=\{([^}]*)\}.*Path=\{(GrandTour\.Water\.[^}]*)\}')
    $rows | ForEach-Object {$_.Line}
    if($rows.Count -ne 4 -or @($rows | Where-Object {$_.Matches[0].Groups[1].Value -ne 'Success'}).Count){throw 'Water regression failed'}
}else{
    $relative=if($Mode -eq 'Install'){'install-report.json'}elseif($WaveFinish){'WakeFinish/vehicle-review.json'}else{'RealismFinal/vehicle-review.json'}
    $report=Join-Path $root ('Art/Export/BenmoreGaea/WaterInteraction/'+$relative)
    if((Get-Item $report).LastWriteTime -lt $started){throw 'Stale interaction report'}
    $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if(!$result.ok){throw $result.error}
}
Write-Output ('BENMORE_WATER_INTERACTION_OK '+$Mode)

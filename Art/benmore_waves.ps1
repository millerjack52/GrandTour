param([ValidateSet('Before','Install','After')][string]$Mode='Before',[switch]$WaitForShared)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
function Test-SharedBusy {
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){return $true}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('bash.exe','cmd.exe') -and $_.CommandLine -match 'Art[/\\](suite\.sh|build\.sh|body_test\.bat)'}){return $true}
    return $false
}
if($WaitForShared){do {Start-Sleep -Seconds 3} while(Test-SharedBusy)}
if(Test-SharedBusy){throw 'Shared Unreal/test is occupied; wait for its owner.'}
$script=if($Mode -eq 'Install'){'install_benmore_flow_waves.py'}else{'review_benmore_wave_motion.py'}
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTMorphology','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$root+'/Saved/Logs/BenmoreWaves'+$Mode+'.log"'))
if($Mode -eq 'After'){$argsList+='-GTWavesAfter'}
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
Write-Output ('BENMORE_WAVES_EDITOR_EXIT '+$Mode)

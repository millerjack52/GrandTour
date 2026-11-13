param([switch]$WaitForShared)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
function Test-SharedBusy {
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){return $true}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('bash.exe','cmd.exe') -and $_.CommandLine -match 'Art[/\\](suite\.sh|build\.sh|body_test\.bat)'}){return $true}
    return $false
}
if($WaitForShared){
    if(Test-SharedBusy){Write-Output 'Waiting for the shared Unreal session to finish.'}
    while(Test-SharedBusy){Start-Sleep -Seconds 3}
    Start-Sleep -Seconds 3
}
if(Test-SharedBusy){throw 'Shared Unreal is occupied; wait for its owner.'}
$started=Get-Date
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/install_benmore_channel_pilot.py"'),('-abslog="'+$root+'/Saved/Logs/BenmoreChannelPilot.log"'))
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$f=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/ChannelPilot/install-report.json')
if($f.LastWriteTime -lt $started){throw 'No fresh channel pilot report'}
$r=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
if(-not $r.ok){throw $r.error}
Write-Output 'BENMORE_CHANNEL_PILOT_OK'

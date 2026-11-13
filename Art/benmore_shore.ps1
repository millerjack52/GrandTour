param([switch]$ReviewOnly,[switch]$WaitForShared)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
function Test-SharedBusy {
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){return $true}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('bash.exe','cmd.exe') -and $_.CommandLine -match 'Art[/\\](suite\.sh|build\.sh|body_test\.bat)'}){return $true}
    return $false
}
if($WaitForShared){do {Start-Sleep -Seconds 3} while(Test-SharedBusy)}
if(Test-SharedBusy){throw 'Shared Unreal/test is occupied; wait for its owner.'}
$started=Get-Date
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTMorphology','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/install_benmore_shore.py"'),('-abslog="'+$root+'/Saved/Logs/BenmoreShore.log"'))
if($ReviewOnly){$argsList+='-GTShoreReviewOnly'}
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$f=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/ShoreRefinement/install-report.json')
if($f.LastWriteTime -lt $started){throw 'No fresh shore report'}
$r=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
if(-not $r.ok){throw $r.error}
Write-Output 'BENMORE_SHORE_REFINEMENT_OK'

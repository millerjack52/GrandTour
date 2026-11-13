param([switch]$WaitForShared,[switch]$BaselineOnly,[switch]$VerifyOnly,[switch]$CourseRevision,[switch]$Morphology)
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
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/install_benmore_gaea_creek.py"'),('-abslog="'+$root+'/Saved/Logs/BenmoreGaeaCreek.log"'))
if($BaselineOnly){$argsList+='-GTChannelBaseline'}
if($VerifyOnly){$argsList+='-GTChannelVerifyOnly'}
if($CourseRevision){$argsList+='-GTCourseRevision'}
if($Morphology){$argsList+='-GTMorphology'}
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$reportFile=if($BaselineOnly){'baseline-report.json'}else{'install-report.json'}
$folder=if($Morphology){'Morphology'}elseif($CourseRevision){'CourseRevision'}else{'GaeaCreek'}
$f=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/'+$folder+'/'+$reportFile)
if($f.LastWriteTime -lt $started){throw 'No fresh channel shape report'}
$r=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
if(-not $r.ok){throw $r.error}
if($BaselineOnly){Write-Output 'BENMORE_CHANNEL_BASELINE_OK'}else{Write-Output 'BENMORE_GAEA_CREEK_OK'}

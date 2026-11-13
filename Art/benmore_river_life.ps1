param([ValidateSet('Setup','Review','Polish','Runtime')][string]$Mode='Setup',[switch]$WaitForEditor)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
function Test-EditorBusy {
    return [bool]((Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) -or (Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object {$_.CommandLine -like '*Art/suite.sh*'}))
}
$waitDeadline=(Get-Date).AddMinutes(90)
while(Test-EditorBusy){
    if(-not $WaitForEditor){throw 'Another Unreal process or the shared test suite is running. Wait before starting this stage.'}
    if((Get-Date) -gt $waitDeadline){throw 'Unreal remained occupied for 90 minutes; no editor was launched.'}
    Start-Sleep -Seconds 2
}
$script=switch($Mode){'Setup'{'setup_benmore_river_life.py'}'Review'{'check_benmore_river_life.py'}'Polish'{'polish_benmore_river_life.py'}'Runtime'{'check_benmore_river_runtime.py'}}
$reportName=$Mode.ToLower()+'-report.json'
$started=Get-Date
$editorArgs=@(('"'+$projectRoot+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-GTLookKuwahara=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$projectRoot+'/Art/Unreal/'+$script+'"'),('-abslog="'+$projectRoot+'/Saved/Logs/BenmoreRiverLife'+$Mode+'.log"'))
$editor=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
$editor.WaitForExit()
$report=Get-Item -LiteralPath ($projectRoot+'/Art/Export/BenmoreGaea/RiverLife/'+$reportName) -ErrorAction SilentlyContinue
if(-not $report -or $report.LastWriteTime -lt $started){throw 'No fresh river stage report.'}
$result=Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json
if(-not $result.ok){throw $result.error}
Write-Output ('RIVER_LIFE_'+$Mode+'_OK; editor exit '+$editor.ExitCode)

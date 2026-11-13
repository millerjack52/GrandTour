$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$deadline=(Get-Date).AddMinutes(60)
while((Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) -or (Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object {$_.CommandLine -like '*Art/suite.sh*'})){
    if((Get-Date)-gt $deadline){throw 'The shared editor remained busy; no budget pass was launched.'}
    Start-Sleep -Seconds 2
}
$started=Get-Date
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 15"',('-ExecutePythonScript="'+$root+'/Art/Unreal/apply_benmore_render_budget.py"'),('-abslog="'+$root+'/Saved/Logs/BenmoreRenderBudget.log"'))
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/RiverScale/budget-report.json')
if($file.LastWriteTime -lt $started){throw 'No fresh budget report'}
$r=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
if(-not $r.ok){throw $r.error}
Write-Output 'BENMORE_RENDER_BUDGET_OK; visual/structural validation only, no timings'

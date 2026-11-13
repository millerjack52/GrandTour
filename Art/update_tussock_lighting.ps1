$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,FarCry6 -ErrorAction SilentlyContinue){throw 'Editor or game is running'}
$archive="$root\Art\Export\TussockStyle\before-lighting"
New-Item -ItemType Directory -Force $archive|Out-Null
foreach($name in @('UE_Driver.png','UE_Overview.png')){
    if(-not(Test-Path "$archive\$name")){Copy-Item -LiteralPath "$root\Art\Export\TussockStyle\$name" -Destination "$archive\$name"}
}
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'\Art\Unreal\update_tussock_lighting.py"'),('-abslog="'+$root+'\Saved\Logs\tussock_lighting_update.log"'))
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$report=Get-Content "$root\Art\Export\TussockStyle\lighting-report.json" -Raw|ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'TUSSOCK_LIGHTING_UPDATED'

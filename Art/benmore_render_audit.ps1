$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$deadline=(Get-Date).AddMinutes(60)
while((Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) -or (Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object {$_.CommandLine -like '*Art/suite.sh*'})){
    if((Get-Date)-gt $deadline){throw 'The shared editor remained busy; no audit was launched.'}
    Start-Sleep -Seconds 2
}
$started=Get-Date
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-run=pythonscript',('-script="'+$root+'/Art/Unreal/audit_benmore_rendering.py"'),'-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-stdout',('-abslog="'+$root+'/Saved/Logs/BenmoreRenderAudit.log"'))
$p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$p.WaitForExit()
$file=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/RiverScale/content-audit.json')
if($file.LastWriteTime -lt $started){throw 'No fresh audit report'}
$report=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
if(-not $report.ok){throw $report.error}
Write-Output 'BENMORE_RENDER_AUDIT_OK; no timings collected'

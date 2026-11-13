$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$busy = Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour,GoW,FarCry6 -ErrorAction SilentlyContinue
if ($busy) { throw ('Close the running editor/game before importing: '+(($busy.ProcessName | Sort-Object -Unique)-join ', ')) }
$editor = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
foreach ($stage in @('import_specials_trio','check_specials_trio_assets')) {
    & $editor "$projectRoot/GrandTour.uproject" -run=pythonscript "-script=$projectRoot/Art/Unreal/$stage.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -FullStdOutLogOutput "-abslog=$projectRoot/Saved/Logs/$stage.log" *> "$projectRoot/Saved/Logs/${stage}_console.log"
    if ($LASTEXITCODE -ne 0) { throw "$stage exited with code $LASTEXITCODE" }
    $reportName = if ($stage -eq 'import_specials_trio') { 'unreal_import_report.json' } else { 'unreal_asset_check.json' }
    $report = Get-Content -Raw -LiteralPath "$projectRoot/Art/Export/SpecialsTrio/$reportName" | ConvertFrom-Json
    if (!$report.ok) { throw "$stage failed: $($report.error)" }
}
Write-Output 'Imported and verified the three cars and six maps. Runtime validation is separate: Art/Unreal/check_specials_trio_drive.py.'

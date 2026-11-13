$ErrorActionPreference = 'Stop'
$shrubRoot = Split-Path $PSScriptRoot
if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'Close Unreal Editor before importing the shrub library.'
}
$shrubArgs = @(
    ('"' + $shrubRoot + '\GrandTour.uproject"'),
    '-RenderOffScreen','-unattended','-nosound','-nop4','-nosplash','-NoLoadStartupPackages',
    ('-ExecutePythonScript="' + $shrubRoot + '\Art\Unreal\import_shrub_library.py"'),
    ('-abslog="' + $shrubRoot + '\Saved\Logs\ShrubLibraryImport.log"')
)
$shrubStarted = [DateTime]::UtcNow
$shrubProcess = Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $shrubArgs -WindowStyle Hidden -PassThru
$shrubProcess.WaitForExit()
$shrubReportFile = Get-Item -LiteralPath "$shrubRoot\Art\Export\ShrubLibrary\v01\unreal-import-report.json"
if ($shrubReportFile.LastWriteTimeUtc -lt $shrubStarted) { throw 'The editor did not write a fresh import report.' }
$shrubReport = Get-Content -LiteralPath "$shrubRoot\Art\Export\ShrubLibrary\v01\unreal-import-report.json" -Raw | ConvertFrom-Json
if (-not $shrubReport.ok) { throw $shrubReport.error }
Write-Output 'SHRUB_LIBRARY_IMPORT_OK: 12 meshes, 3 LODs each'

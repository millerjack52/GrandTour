$ErrorActionPreference = 'Stop'
if (Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue) {
    throw 'Close the Unreal editor/game before running the Prado importer.'
}
$pradoArguments = @(
    '"C:/GrandTour/GrandTour.uproject"',
    '-RenderOffScreen', '-dx12', '-Unattended', '-NoSplash', '-NoSound',
    '-GTLook=0', '-GTLookKuwahara=0', '-GTNoLoad',
    '-ResX=1440', '-ResY=900',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
    '-ExecCmds="t.MaxFPS 30,r.ScreenPercentage 100"',
    '-EnablePlugins=PythonScriptPlugin',
    '-ExecutePythonScript="C:/GrandTour/Art/Unreal/run_prado_import_review.py"',
    '-abslog="C:/GrandTour/Saved/Logs/import_prado_editor.log"'
)
$pradoProcess = Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $pradoArguments -WindowStyle Hidden -PassThru
Write-Output "Prado import/review process: $($pradoProcess.Id)"
$pradoProcess.WaitForExit()
$pradoReport = Get-Content -Raw -LiteralPath 'C:/GrandTour/Art/Export/VehicleTools/prado-unreal-v01/unreal-import-report.json' | ConvertFrom-Json
if ($pradoReport.status -ne 'IMPORTED_AND_REOPENED') { throw ($pradoReport | ConvertTo-Json -Depth 6) }
$pradoRender = Get-Content -Raw -LiteralPath 'C:/GrandTour/Art/Export/VehicleTools/prado-unreal-v01/render-check.json' | ConvertFrom-Json
if (-not $pradoRender.ok) { throw ($pradoRender | ConvertTo-Json -Depth 6) }
Write-Output 'PRADO_IMPORTED_AND_RENDER_CHECKED'

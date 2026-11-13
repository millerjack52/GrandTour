$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# Benmore integration B1c (docs/BENMORE_INTEGRATION_PLAN.md): the setup run (Art/Unreal/setup_benmore_b1c.py: the gravel surfaces' tints,
# then the wheel spray's rebuild as Art/setup_wheel_spray.ps1). The pictures: Art/benmore_b1b.ps1 -Stage B1c. Call
# Art/wait_unreal_free.ps1 first, as its own command. A game may be open (the run does not check for one).
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal editor is running (run Art/wait_unreal_free.ps1 first)'}
# As Art/setup_wheel_spray.ps1: the system is rebuilt from nothing, its old file removed before the editor starts.
Remove-Item -LiteralPath ($root+'/Content/GrandTour/FX/NS_GT_WheelSpray.uasset') -ErrorAction SilentlyContinue
$started=Get-Date
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
    ('-ExecutePythonScript="'+$root+'\Art\Unreal\setup_benmore_b1c.py"'),('-abslog="'+$root+'\Saved\Logs\benmore_b1c_setup.log"'))
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
foreach($f in @("$root\Art\Export\BenmoreB1c\surfaces.json","$root\Art\Export\WheelSpray\setup-report.json")){
    $file=Get-Item $f -ErrorAction SilentlyContinue
    if(-not $file -or $file.LastWriteTime -lt $started){throw "No fresh $f (editor exit $($p.ExitCode))"}
}
$report=Get-Content "$root\Art\Export\WheelSpray\setup-report.json" -Raw|ConvertFrom-Json
if(-not $report.ok){throw ('Wheel spray setup failed: '+$report.error+' '+(($report.niagara_log|Select-String 'FAIL') -join ' '))}
Write-Output ('BENMORE_B1C_SETUP_OK; editor exit '+$p.ExitCode)

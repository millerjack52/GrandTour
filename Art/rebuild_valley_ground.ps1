$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
Set-Location $taskRoot
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
if(-not $held){throw 'Unreal reserved'}
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
& "$taskRoot/Saved/Tools/TerrainPython/Scripts/python.exe" Art/tools/build_valley_ground_map.py
if($LASTEXITCODE -ne 0){throw 'Map build failed'}
$started=Get-Date
$launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-ExecCmds="t.MaxFPS 30"',('-abslog="'+$taskRoot+'/Saved/Logs/ValleyGroundBuild.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/install_valley_ground.py"'))
$p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
$null=$p.Handle;$p.WaitForExit()
$file=Get-Item Saved/LidarAuthoringQA/ValleyGround/build-result.json
if($file.LastWriteTime -lt $started){throw 'No current build result'}
$result=Get-Content $file.FullName -Raw|ConvertFrom-Json
if(-not $result.ok){throw $result.error}
if($p.ExitCode -ne 0){throw "Editor exit $($p.ExitCode)"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

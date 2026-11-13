$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
Set-Location $taskRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Close Unreal before shader authoring.'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 & "$taskRoot/Saved/Tools/TerrainPython/Scripts/python.exe" Art/tools/build_forest_shader_atlases.py
 if($LASTEXITCODE -ne 0){throw 'Atlas build failed'}
 $started=Get-Date
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-ExecCmds="t.MaxFPS 30"',('-abslog="'+$taskRoot+'/Saved/Logs/ForestShadersBuild.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/install_forest_shaders.py"'))
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit()
 $file=Get-Item Saved/LidarAuthoringQA/ForestShaders/build-result.json -ErrorAction SilentlyContinue
 if(-not $file -or $file.LastWriteTime -lt $started){throw "No current build result; editor exit $($p.ExitCode)"}
 $result=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if(-not $result.ok){throw $result.error}
 if($p.ExitCode -ne 0){throw "Editor exit $($p.ExitCode)"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

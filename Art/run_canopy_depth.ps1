param([ValidateSet('build','install','verify','lighting')][string]$Stage='build')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
Set-Location $taskRoot
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
 $started=Get-Date
 $script=if($Stage -eq 'build'){'build_canopy_depth.py'}elseif($Stage -eq 'lighting'){'canopy_lighting.py'}else{'install_canopy_depth.py'}
 $oldStage=$env:GT_CD_STAGE;$env:GT_CD_STAGE=$Stage
 try {
  $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12','-ExecCmds="t.MaxFPS 30"',('-abslog="'+$taskRoot+'/Saved/Logs/CanopyDepth-'+$Stage+'.log"'),('-ExecutePythonScript="'+$taskRoot+'/Art/Unreal/'+$script+'"'))
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 } finally {$env:GT_CD_STAGE=$oldStage}
 $null=$p.Handle;$p.WaitForExit()
 $file=Get-Item ('Saved/LidarAuthoringQA/CanopyDepth/'+$Stage+'-result.json')
 if($file.LastWriteTime -lt $started){throw 'No current result'}
 $result=Get-Content $file.FullName -Raw|ConvertFrom-Json
 if(-not $result.ok){throw $result.error}
 if($p.ExitCode -ne 0){throw "Editor exit $($p.ExitCode)"}
 Write-Output "CanopyDepth $Stage passed"
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

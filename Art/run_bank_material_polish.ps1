param([ValidateSet('ground','leaf','final','check')][string]$Mode='final')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot
& "$PSScriptRoot/wait_unreal_free.ps1" -PollSeconds 10 -MaxMinutes 1
if($LASTEXITCODE -ne 0){throw 'Unreal occupied'}
if(Get-Process FarCry6,Skate -ErrorAction SilentlyContinue){throw 'GPU occupied by a game; close it before running the authoring editor'}
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$acquired=$false
try {
 $acquired=$reservation.WaitOne(0);if(-not $acquired){throw 'Unreal reserved'}
 $qa="$taskRoot/Saved/LidarAuthoringQA/VP2Materials"
 New-Item -ItemType Directory -Force -Path $qa | Out-Null
 @{mode=$Mode} | ConvertTo-Json | Set-Content "$qa/request.json"
 if(Test-Path "$qa/job-result.json"){Move-Item -LiteralPath "$qa/job-result.json" -Destination "$qa/previous-job-result.json" -Force}
 $launch=@(('"'+$taskRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-RenderOffScreen','-dx12',('-abslog="'+$taskRoot+'/Saved/Logs/VP2Materials-'+$Mode+'.log"'),('-ExecutePythonScript="'+$PSScriptRoot+'/Unreal/run_bank_material_polish.py"'))
 $process=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$process.Handle;$process.WaitForExit()
 if($process.ExitCode -ne 0){throw "Editor exited $($process.ExitCode)"}
 $result=Get-Content "$qa/job-result.json" -Raw | ConvertFrom-Json
 if(-not $result.ok){throw $result.error}
 Write-Output "VP2 $Mode completed; report $qa/job-result.json"
} finally {if($acquired){$reservation.ReleaseMutex()};$reservation.Dispose()}

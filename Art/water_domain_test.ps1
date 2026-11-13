param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Shared Unreal is occupied'}
$log=Join-Path $root 'Saved/Logs/water_domain_test.log'
$arguments=@(('"'+$root+'/GrandTour.uproject"'),'-NullRHI','-Unattended','-NoSplash','-NoSound','-NoP4','-GTNoLoad','-ExecCmds="Automation RunTests GrandTour.Water.RiverReference+GrandTour.Water.MovingDomain+GrandTour.Water.PassiveDetail"','-TestExit="Automation Test Queue Empty"',('-abslog="'+$log+'"'))
$started=Get-Date
$process=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
if((Get-Item $log).LastWriteTime -lt $started){throw 'No fresh automation log'}
$results=@(Select-String -LiteralPath $log -Pattern 'Test Completed\. Result=\{([^}]*)\}.*Path=\{(GrandTour\.Water\.[^}]*)\}')
$results | ForEach-Object {$_.Line}
if($results.Count -ne 3 -or @($results | Where-Object {$_.Matches[0].Groups[1].Value -ne 'Success'}).Count){throw 'Water domain regression failed; inspect log'}
Write-Output 'WATER_DOMAIN_OK: 3 CPU regressions passed; no motion or timing claim'

param([ValidateSet('compare','save','verify')][string]$Stage='compare')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$settings=Get-Content Art/flora_transmission_settings.json -Raw | ConvertFrom-Json
$out='C:/GrandTour/Art/Export/FloraTransmissionStudy/'+$settings.revision
New-Item -ItemType Directory -Force $out | Out-Null
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender,'Wardogs*' -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited}){throw 'Another renderer or Wardogs is running; no application was closed'}
 python Art/flora_transmission_baseline.py
 if($LASTEXITCODE -ne 0){throw 'Baseline failed'}
 $os=Get-CimInstance Win32_OperatingSystem
 @{physical=$os.FreePhysicalMemory*1KB;virtual=$os.FreeVirtualMemory*1KB;disk=(Get-PSDrive C).Free;time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$out/$Stage-preflight.json"
 if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB -or (Get-PSDrive C).Free -lt 4GB){throw 'Insufficient rendering headroom'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender,'Wardogs*' -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited}){throw 'Another renderer started during preparation'}
 $env:GT_TRANSMISSION_STAGE=$Stage;$started=Get-Date
 $args=@('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-norhithread','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0','-ExecutePythonScript=C:/GrandTour/Art/Unreal/trial_flora_transmission.py',('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"')
 $process=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
 $null=$process.Handle;$deadline=(Get-Date).AddMinutes(25);$stopReason=$null
 @{pid=$process.Id;state='running';started=$started.ToString('o')} | ConvertTo-Json | Set-Content "$out/$Stage-process.json"
 while(-not $process.HasExited){
  $competing=@(Get-Process UnrealEditor,UnrealEditor-Cmd,blender,'Wardogs*' -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited -and $_.Id -ne $process.Id})
  if($competing.Count -or (Get-PSDrive C).Free -lt 2GB -or (Get-Date) -gt $deadline){
   $stopReason=if($competing.Count){'Another renderer started'}elseif((Get-PSDrive C).Free -lt 2GB){'Disk headroom fell below 2 GB'}else{'Render timed out'}
   $details=@($competing | ForEach-Object {Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" | Select-Object ProcessId,ParentProcessId,Name,CommandLine})
   @{reason=$stopReason;competing=$details} | ConvertTo-Json -Depth 4 | Set-Content "$out/$Stage-stopped.json"
   Stop-Process -Id $process.Id -Force
  }
  Start-Sleep -Milliseconds 500;$process.Refresh()
 }
 @{exit_code=$process.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$out/$Stage-process.json"
 if($stopReason){throw "$stopReason; only this study's Unreal process was stopped"}
 $f=Get-Item "$out/$Stage-report.json";$report=Get-Content $f.FullName -Raw | ConvertFrom-Json
 if($process.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not $report.ok){throw "Transmission study failed: $($report.error)"}
 if((Get-Content "$out/$Stage.log" -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'){throw 'Shader/runtime error'}
 python Art/flora_transmission_baseline.py
 if($LASTEXITCODE -ne 0){throw 'Protected packages changed'}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

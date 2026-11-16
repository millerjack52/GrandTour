param([ValidateSet('candidate','verify','save','diagnose')][string]$Stage='candidate')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$out='D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion'
$settings=Get-Content Art/flora_motion_settings.json -Raw | ConvertFrom-Json
if($settings.evidence_subdir) {$out=Join-Path $out $settings.evidence_subdir}
New-Item -ItemType Directory -Force $out | Out-Null
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held) {throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited}) {throw 'Renderer already running'}
 if(Get-Process 'Wardogs*' -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited}) {throw 'Wardogs is running; render testing is held. No application was closed.'}
 python Art/flora_motion_baseline.py
 if($LASTEXITCODE -ne 0) {throw 'Protected baseline changed'}
 $os=Get-CimInstance Win32_OperatingSystem
 @{time=(Get-Date).ToString('o');physical=$os.FreePhysicalMemory*1KB;virtual=$os.FreeVirtualMemory*1KB;disk=(Get-PSDrive C).Free;processes=@(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 8 Id,ProcessName,WorkingSet64)} | ConvertTo-Json -Depth 4 | Set-Content ($out+'/'+$Stage+'-preflight.json')
 if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB -or (Get-PSDrive C).Free -lt 4GB) {throw 'Insufficient render budget; no application was closed'}
 $started=Get-Date;$env:GT_FLORA_MOTION_STAGE=$Stage
 $script='trial_flora_motion.py'
 $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList @('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-norhithread','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0',('-ExecutePythonScript=C:/GrandTour/Art/Unreal/'+$script),('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"') -WindowStyle Hidden -PassThru
 $null=$p.Handle
 @{exit_code=$null;pid=$p.Id;started=$started.ToString('o');state='running'} | ConvertTo-Json | Set-Content ($out+'/'+$Stage+'-process.json')
 # An exited UE process can remain in Windows' process list while its final
 # teardown thread lingers. WaitForExit hung on that state; use HasExited and
 # preserve the authoritative exit code plus remaining entries below.
 $deadline=(Get-Date).AddMinutes(30)
 while(-not $p.HasExited) {if((Get-Date) -gt $deadline) {throw 'Renderer timeout; inspect before relaunching'};Start-Sleep -Milliseconds 500;$p.Refresh()}
 @{exit_code=$p.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content ($out+'/'+$Stage+'-process.json')
 @(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,HasExited,WorkingSet64) | ConvertTo-Json | Set-Content ($out+'/'+$Stage+'-remaining-renderer-entries.json')
 $f=Get-Item ($out+'/'+$Stage+'-report.json');$report=Get-Content $f.FullName -Raw | ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not $report.ok) {throw "Flora motion $Stage failed: $($report.error)"}
 if((Get-Content ($out+'/'+$Stage+'.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error') {throw 'Flora motion shader/render validation failed'}
 python Art/flora_motion_baseline.py
 if($LASTEXITCODE -ne 0) {throw 'Protected baseline changed'}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

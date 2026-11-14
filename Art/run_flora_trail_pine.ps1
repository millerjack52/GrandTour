param([ValidateSet('export','install','verify')][string]$Stage='export')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$out='C:/GrandTour/Art/Export/FloraTrail/PineTrial'
New-Item -ItemType Directory -Force $out | Out-Null
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held) {throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue) {throw 'Renderer already running'}
 python Art/flora_trail_palette_baseline.py --verify
 if($LASTEXITCODE -ne 0) {throw 'Protected baseline changed'}
 $os=Get-CimInstance Win32_OperatingSystem
 @{time=(Get-Date).ToString('o');physical=$os.FreePhysicalMemory*1KB;virtual=$os.FreeVirtualMemory*1KB;disk=(Get-PSDrive C).Free;processes=@(Get-Process | Where-Object {$_.ProcessName -match 'Unreal|Blender|Wardog'} | Select-Object Id,ProcessName,WorkingSet64)} | ConvertTo-Json -Depth 4 | Set-Content ($out+'/'+$Stage+'-preflight.json')
 if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB -or (Get-PSDrive C).Free -lt 4GB) {throw 'Insufficient render budget; no application was closed'}
 $started=Get-Date
 if($Stage -eq 'export') {
  $p=Start-Process 'D:/GrandTourAssets/Tools/blender-3.4.1-windows-x64/blender.exe' -ArgumentList @('-b','--threads','6','--python-exit-code','1','--python','C:/GrandTour/Art/Blender/export_flora_trail_pine.py') -RedirectStandardOutput ($out+'/export.log') -RedirectStandardError ($out+'/export-errors.log') -WindowStyle Hidden -PassThru
 } else {
  $env:GT_PINE_STAGE=$Stage
  $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList @('C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-norhithread','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker','-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0','-ExecutePythonScript=C:/GrandTour/Art/Unreal/trial_flora_trail_pine.py',('-abslog='+$out+'/'+$Stage+'.log'),'-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"') -WindowStyle Hidden -PassThru
 }
 $null=$p.Handle
 if(-not $p.WaitForExit(1800000)) {throw 'Renderer timeout; inspect before relaunching'}
 @{exit_code=$p.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content ($out+'/'+$Stage+'-process.json')
 $f=Get-Item ($out+'/'+$Stage+'-report.json');$report=Get-Content $f.FullName -Raw | ConvertFrom-Json
 if($p.ExitCode -ne 0 -or $f.LastWriteTime -lt $started -or -not $report.ok) {throw "Pine $Stage failed: $($report.error)"}
 if($Stage -ne 'export' -and (Get-Content ($out+'/'+$Stage+'.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error') {throw 'Pine shader/render validation failed'}
 python Art/flora_trail_palette_baseline.py --verify
 if($LASTEXITCODE -ne 0) {throw 'Protected baseline changed'}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

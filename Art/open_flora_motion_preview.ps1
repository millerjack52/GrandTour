$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$engine='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$map='/Game/GrandTour/ArtTests/FloraTrail/Woodland/Motion/v2/L_FloraTrail_Motion'
$mapFile=Join-Path $root 'Content/GrandTour/ArtTests/FloraTrail/Woodland/Motion/v2/L_FloraTrail_Motion.umap'
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
    try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held) {throw 'Another GrandTour render or preview is already running.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited}) {throw 'Close the existing Unreal or Blender renderer before opening the motion preview.'}
    if(-not (Test-Path -LiteralPath $engine) -or -not (Test-Path -LiteralPath $mapFile)) {throw 'The local Unreal installation or saved Motion/v2 candidate is missing.'}
    $os=Get-CimInstance Win32_OperatingSystem
    if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB -or (Get-PSDrive C).Free -lt 4GB) {throw 'Insufficient memory or disk space for this preview. No application was closed.'}
    $log=Join-Path $root 'Saved/Logs/FloraMotionPreview.log'
    $record=Join-Path $root 'Saved/Logs/FloraMotionPreview-process.json'
    New-Item -ItemType Directory -Force (Split-Path $log -Parent) | Out-Null
    $started=(Get-Date).ToString('o')
    Write-Host 'Opening the experimental FloraTrail wind and falling-leaf preview. This version has a known high GPU cost.'
    $arguments=@(('"'+(Join-Path $root 'GrandTour.uproject')+'"'),$map,'-game','-ResX=1600','-ResY=900','-windowed','-GTNoLoad','-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0',('-abslog="'+$log+'"'),'-ExecCmds="gt.Look.Post 0,r.LUT.TonemappingMethod 0,r.LUT.TonemappingSDRInvEOTF 0,r.AntiAliasingMethod 4,r.ScreenPercentage 100,r.MotionBlurQuality 0,r.EyeAdaptationQuality 0,r.DistanceFieldAO 0,r.Lumen.DiffuseIndirect.Allow 0,r.Lumen.Reflections.Allow 0,r.Shadow.Virtual.Cache 1,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"')
    # This is the interactive preview requested by the user; show the game window.
    $p=Start-Process -FilePath $engine -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Normal -PassThru
    $null=$p.Handle
    @{pid=$p.Id;map=$map;started=$started;state='running';experimental=$true} | ConvertTo-Json | Set-Content $record
    while(-not $p.HasExited) {Start-Sleep -Milliseconds 500;$p.Refresh()}
    @{pid=$p.Id;map=$map;started=$started;finished=(Get-Date).ToString('o');exit_code=$p.ExitCode;state='exited';experimental=$true} | ConvertTo-Json | Set-Content $record
} catch {
    Write-Error $_
    exit 1
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

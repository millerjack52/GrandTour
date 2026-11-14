param([ValidateSet('prepare','diagnose')][string]$Stage='prepare')
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$held=$false
try {
    try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held) {throw 'Renderer slot reserved'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue) {throw 'Renderer already running'}
    python Art/flora_trail_palette_baseline.py
    if($LASTEXITCODE -ne 0) {throw 'Baseline integrity/backup failed'}
    if($Stage -eq 'prepare') {return}
    $out='C:/GrandTour/Art/Export/FloraTrail/PaletteCandidate'
    $os=Get-CimInstance Win32_OperatingSystem
    $disk=Get-PSDrive C
    $processes=@(Get-Process | Where-Object {$_.ProcessName -match 'Unreal|Blender|Wardog'} |
        Select-Object Id,ProcessName,WorkingSet64,MainWindowTitle)
    $preflight=@{time=(Get-Date).ToString('o');free_physical_bytes=$os.FreePhysicalMemory*1KB;
        free_virtual_bytes=$os.FreeVirtualMemory*1KB;free_disk_bytes=$disk.Free;processes=$processes}
    $preflight | ConvertTo-Json -Depth 5 | Set-Content ($out+'/preflight.json')
    # Do not kill games or other user applications to obtain this budget.
    if($os.FreePhysicalMemory*1KB -lt 8GB -or $os.FreeVirtualMemory*1KB -lt 12GB) {
        throw 'Insufficient memory for Unreal: need 8 GiB free physical / 12 GiB free virtual. No renderer launched; user applications remain running.'
    }
    if($disk.Free -lt 4GB) {throw 'Insufficient C: cache/output space: need at least 4 GiB free'}
    $started=Get-Date
    $p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList @(
        'C:/GrandTour/GrandTour.uproject','/Engine/Maps/Entry','-RenderOffScreen','-norhithread','-dx12',
        '-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-noshaderworker',
        '-GTLook=0','-GTLookSky=0','-GTLookHaze=0','-GTLookKuwahara=0','-GTLidarPerformance=0',
        '-ExecutePythonScript=C:/GrandTour/Art/Unreal/probe_flora_trail_palette.py',
        ('-abslog='+$out+'/diagnose.log'),
        '-ExecCmds="t.IdleWhenNotForeground 0,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64"'
    ) -WindowStyle Hidden -PassThru
    $null=$p.Handle
    if(-not $p.WaitForExit(1800000)) {throw "Diagnostic process $($p.Id) exceeded 30 minutes; inspect it before launching another renderer"}
    @{exit_code=$p.ExitCode;started=$started.ToString('o');finished=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content ($out+'/diagnose-process.json')
    $file=Get-Item ($out+'/diagnose-report.json')
    $report=Get-Content $file.FullName -Raw | ConvertFrom-Json
    if($p.ExitCode -ne 0 -or $file.LastWriteTime -lt $started -or -not $report.ok) {throw "Palette diagnosis failed: exit $($p.ExitCode) $($report.error)"}
    if((Get-Content ($out+'/diagnose.log') -Raw) -match 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error') {throw 'Shader validation failed'}
    python Art/flora_trail_palette_baseline.py --verify
    if($LASTEXITCODE -ne 0) {throw 'Protected baseline changed'}
    python Art/review_flora_trail_palette.py
    if($LASTEXITCODE -ne 0) {throw 'Diagnostic evidence assembly failed'}
} finally {
    if($held) {$mutex.ReleaseMutex()}
    $mutex.Dispose()
}

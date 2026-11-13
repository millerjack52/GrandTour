param([ValidateSet('Prepare','Install','Verify')][string]$Mode='Install')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$out=Join-Path $root 'Art/Export/BenmoreGaea/WaterSurface_20261011'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
    try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Another build/profile owns the Unreal slot'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An editor is active'}
    $script=if($Mode -eq 'Prepare'){'prepare_benmore_surface.py'}else{'install_benmore_surface.py'}
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-Unattended','-NoSound','-NoSplash','-NoP4','-GTNoLoad','-GTMorphology',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
        '-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$out+'/'+$Mode+'.log"'),('-GTSurface'+$Mode))
    if($Mode -eq 'Prepare'){$exe='UnrealEditor-Cmd.exe';$argsList+='-NullRHI'}else{$exe='UnrealEditor.exe';$argsList+=@('-RenderOffScreen','-dx12')}
    $start=Get-Date
    $p=Start-Process -FilePath ('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/'+$exe) -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $p.WaitForExit();if($p.ExitCode -ne 0){throw ('Editor failed '+$p.ExitCode)}
    $report=Join-Path $out ($Mode.ToLower()+'-report.json')
    if((Get-Item -LiteralPath $report).LastWriteTime -lt $start){throw 'Stale report'}
    $r=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if(!$r.ok){throw $r.error}
    Write-Output ('BENMORE_SURFACE_OK '+$Mode)
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

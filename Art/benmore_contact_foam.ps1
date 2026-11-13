param([ValidateSet('Install','Verify')][string]$Mode='Install',[string]$OutputFolder='WaterSurface_Foam_20261011')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$out=Join-Path $root ('Art/Export/BenmoreGaea/'+$OutputFolder)
$priorOut=$env:GT_CONTACT_FOAM_OUT
New-Item -ItemType Directory -Force -Path $out | Out-Null
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
    try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Another build/profile owns the Unreal slot'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An editor is active'}
    $env:GT_CONTACT_FOAM_OUT=$out
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-Unattended','-NoSound','-NoSplash','-NoP4','-GTNoLoad','-GTMorphology',
        '-RenderOffScreen','-dx12',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
        '-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/install_benmore_contact_foam.py"'),
        ('-abslog="'+$out+'/'+$Mode+'.log"'),('-GTFoam'+$Mode))
    $start=Get-Date
    $p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $p.WaitForExit();if($p.ExitCode -ne 0){throw ('Editor failed '+$p.ExitCode)}
    $report=Join-Path $out ($Mode.ToLower()+'-report.json')
    if((Get-Item -LiteralPath $report).LastWriteTime -lt $start){throw 'Stale report'}
    $r=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if(!$r.ok){throw $r.error}
    Write-Output ('BENMORE_CONTACT_FOAM_OK '+$Mode)
} finally {$env:GT_CONTACT_FOAM_OUT=$priorOut;if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

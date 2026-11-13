param([ValidateSet('Baseline','Check')][string]$Mode='Check')
$ErrorActionPreference='Stop'
$labRoot=Split-Path $PSScriptRoot
$labOut=Join-Path $PSScriptRoot 'Export/MudRoad/NativeStage4'
$reservation=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling')
$acquired=$false
try {
    try {$acquired=$reservation.WaitOne(0)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Unreal slot is reserved by another task'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Close the running editor/game before running this check'}
    $labScript='check_mud_suspension.py'
    $labReportName='suspension-report.json'
    $labArgs=@(('"'+$labRoot+'/GrandTour.uproject"'),'/Engine/Maps/Entry','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad',
        '-ExecCmds="r.Nanite.Tessellation 1,r.Nanite.ProgrammableRaster 1,r.Nanite.ComputeRasterization 1"',
        ('-ExecutePythonScript="'+$labRoot+'/Art/Unreal/'+$labScript+'"'),
        ('-abslog="'+$labRoot+'/Saved/Logs/MudSuspension-'+$Mode+'.log"'))
    $labArgs+=@('-RenderOffScreen','-dx12')
    $started=Get-Date
    $labStart=[Diagnostics.ProcessStartInfo]::new('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',($labArgs -join ' '))
    $labStart.UseShellExecute=$false;$labStart.CreateNoWindow=$true;$labStart.WindowStyle='Hidden'
    $labProcess=[Diagnostics.Process]::Start($labStart)
    if(-not $labProcess.WaitForExit(600000)){Stop-Process -Id $labProcess.Id;throw 'Owned Mud Road run exceeded ten minutes'}
    $labProcess.WaitForExit()
    $labExit=$labProcess.ExitCode
    $labFile=Get-Item -LiteralPath (Join-Path $labOut $labReportName)
    $labReport=Get-Content -LiteralPath $labFile.FullName -Raw | ConvertFrom-Json
    @{mode=$Mode;exit_code=$labExit;started=$started.ToString('o');report_written=$labFile.LastWriteTime.ToString('o');report_ok=$labReport.ok} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labOut ('suspension-'+$Mode.ToLower()+'-process.json'))
    if($labExit -ne 0 -or $labFile.LastWriteTime -lt $started -or -not $labReport.ok){throw "Mud Road $Mode failed (exit=$labExit, report=$($labReport.ok)); inspect $($labFile.FullName)"}
    Copy-Item -LiteralPath $labFile.FullName -Destination (Join-Path $labOut ('suspension-'+$Mode.ToLower()+'.json'))
    if($Mode -eq 'Check'){
        foreach($case in $labReport.cases){
            # The deliberately maximally excavated case may run out of droop.
            if($case.name -ne 'churned_dip' -and ($case.contact_fraction | Measure-Object -Minimum).Minimum -lt .99){
                throw "Lost stationary wheel support: $($case.name)"
            }
            if(($case.offset_range_cm | Measure-Object -Maximum).Maximum -gt 2 -or
                ($case.contact_changes | Measure-Object -Sum).Sum -gt 0 -or $case.peak_vz_cm_s -gt 5){
                throw "Stationary suspension did not settle: $($case.name)"
            }
        }
    }
    Write-Output "Mud Road $Mode passed"
} finally {
    if($acquired){$reservation.ReleaseMutex()}
    $reservation.Dispose()
}



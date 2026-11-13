param([ValidateSet('water','terrain','spray')][string[]]$Tests=@('water','terrain','spray'))
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot)
$out=Join-Path $root 'Art/Export/BenmoreGaea/WaterBalanced_20261011'
$results=@()
if($Tests.Count -lt 3 -and (Test-Path (Join-Path $out 'regressions.json'))){
    $previous=Get-Content -LiteralPath (Join-Path $out 'regressions.json') -Raw | ConvertFrom-Json
    foreach($prior in $previous){if($prior.name -and $prior.name -notin $Tests){$results+=$prior}}
}
# Separate read-only gameplay processes and log names: other project checks can
# finish without overwriting either run's evidence. These are not performance runs.
foreach($case in @(
    @{Name='water';Map='/Game/GrandTour/Legs/L_Leg03';Switch='-GTWaterTest';Extra='-GTNoLoad'},
    @{Name='terrain';Map='/Game/GrandTour/Legs/L_Leg03';Switch='-GTTerrainTest';Extra='-GTNoLoad -GTLookDressing=0'},
    @{Name='spray';Map='/Game/GrandTour/Test/L_TestTrack';Switch='-GTSprayTest';Extra=''}
)) {
    if($case.Name -notin $Tests){continue}
    $log=Join-Path $out ($case.Name+'-regression.log')
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),$case.Map,'-game','-NullRHI','-unattended','-nopause','-nosplash','-nosound',$case.Switch,$case.Extra,('-abslog="'+$log+'"'))
    $argsList=@($argsList | Where-Object {$_})
    $started=Get-Date
    $p=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    $line=if((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).LastWriteTime -ge $started){
        (Select-String -LiteralPath $log -Pattern 'GTDRIVETEST_RESULT' | Select-Object -Last 1).Line
    }else{'Missing fresh log'}
    $ok=$p.ExitCode -eq 0 -and $line -match 'GTDRIVETEST_RESULT PASS'
    $results+=@{name=$case.Name;ok=$ok;exit_code=$p.ExitCode;result=$line;log=$log}
    ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'regressions.json')
    Write-Output ($case.Name+': '+$line)
}
if(@($results | Where-Object {!$_.ok}).Count){exit 1}

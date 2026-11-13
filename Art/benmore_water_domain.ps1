param([ValidateSet('Test','Install','Runtime','Polish','Appearance')][string]$Mode='Test',[switch]$SkipTimings)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Shared Unreal is occupied; wait for its owner.'}
if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('bash.exe','cmd.exe') -and $_.CommandLine -match 'Art[/\\](suite\.sh|body_test\.bat)'}){throw 'Shared suite is active between tests.'}
if($SkipTimings -and $Mode -ne 'Appearance'){throw 'SkipTimings is only supported for Appearance.'}
$isTiming=($Mode -in @('Runtime','Appearance')) -and -not $SkipTimings
if($isTiming -and (Get-Process GoWR,GoW,FarCry6,GrandTour,blender -ErrorAction SilentlyContinue)){throw 'Another game or Blender is active; no timings launched.'}
$started=Get-Date
$externalReport=Join-Path $root ('Art/Export/BenmoreGaea/RiverScale/'+$(if($Mode -eq 'Appearance'){'appearance-external-load.json'}else{'domain-runtime-external-load.json'}))
if($isTiming -and (Test-Path -LiteralPath $externalReport)){Remove-Item -LiteralPath $externalReport}
if($Mode -eq 'Test'){
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-NullRHI','-Unattended','-NoSplash','-NoSound','-nop4','-ExecCmds="Automation RunTests GrandTour.Water."','-TestExit="Automation Test Queue Empty"',('-ReportExportPath="'+$root+'/Saved/Automation/BenmoreDomain"'),('-abslog="'+$root+'/Saved/Logs/BenmoreDomainTest.log"'))
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
}else{
    $script=if($Mode -eq 'Runtime'){'validate_benmore_domain_runtime.py'}elseif($Mode -eq 'Polish'){'polish_benmore_water_detail.py'}elseif($Mode -eq 'Appearance'){'refresh_benmore_water_appearance.py'}else{'install_benmore_water_domain.py'}
    $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ExecCmds="t.MaxFPS 30"',('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$root+'/Saved/Logs/BenmoreDomain'+$Mode+'.log"'))
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
    if($Mode -eq 'Runtime'){
        $argsList=@(('"'+$root+'/GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-nop4','-GTNoLoad','-csvGpuStats','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',('-ExecutePythonScript="'+$root+'/Art/Unreal/'+$script+'"'),('-abslog="'+$root+'/Saved/Logs/BenmoreDomainRuntime.log"'))
    }
    if($Mode -eq 'Appearance'){$argsList += '-csvGpuStats'}
    if($SkipTimings){$argsList += '-GTWaterAppearanceNoTimings'}
}
$p=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
if($isTiming){
    while(-not $p.HasExited){
        $load=Get-Process GoWR,GoW,FarCry6,GrandTour,blender -ErrorAction SilentlyContinue
        if($load){$load | Select-Object Id,ProcessName | ConvertTo-Json | Set-Content -LiteralPath $externalReport}
        Start-Sleep -Seconds 3
        $p.Refresh()
    }
}else{$p.WaitForExit()}
if($Mode -eq 'Test'){
    $f=Get-Item -LiteralPath ($root+'/Saved/Automation/BenmoreDomain/index.json')
    if($f.LastWriteTime -lt $started){throw 'Stale test report'}
    $r=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
    if($r.failed -gt 0 -or $r.succeeded -lt 3){throw 'Water domain automation failed; inspect BenmoreDomainTest.log'}
    Write-Output ('BENMORE_DOMAIN_TEST_OK: '+$r.succeeded+' CPU tests')
}else{
    $reportName=if($Mode -eq 'Runtime'){'domain-runtime-report.json'}elseif($Mode -eq 'Polish'){'detail-polish-report.json'}elseif($Mode -eq 'Appearance'){'appearance-report.json'}else{'domain-install-report.json'}
    $f=Get-Item -LiteralPath ($root+'/Art/Export/BenmoreGaea/RiverScale/'+$reportName)
    if($f.LastWriteTime -lt $started){throw 'No fresh setup report'}
    $r=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
    if(-not $r.ok){throw $r.error}
    Write-Output ('BENMORE_WATER_DOMAIN_'+$Mode.ToUpper()+'_OK')
}

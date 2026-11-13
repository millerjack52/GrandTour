$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 python Art/tools/prepare_road_parallax_capture.py
 if($LASTEXITCODE -ne 0){throw 'Capture plan failed'}
 $qa='C:/GrandTour/Saved/LidarAuthoringQA/RoadParallax/Native';$plan=Get-Content "$qa/plan.json" -Raw | ConvertFrom-Json
 $initial=(@($plan.quality)+@('EnableCheats','ShowHUD','DisableAllScreenMessages','r.MotionBlurQuality 0','t.IdleWhenNotForeground 0',('CsvProfile FRAMES='+$plan.frames))) -join ','
 $launch=@('C:/GrandTour/GrandTour.uproject','/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="'+$initial+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($plan.commands -join ',')+'"'),'-abslog=C:/GrandTour/Saved/Logs/RoadParallax-Final.log')
 if(($launch -join ' ').Length -gt 16000){throw 'Command line too long'}
 $started=Get-Date;$p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();$log=Get-Content Saved/Logs/RoadParallax-Final.log -Raw
 $bad=$log -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'
 $stale=@(@($plan.images | ForEach-Object {"$qa/$_"})+@($plan.motion) | Where-Object {$f=Get-Item -LiteralPath $_ -ErrorAction SilentlyContinue; -not $f -or $f.LastWriteTime -lt $started})
 $cameras=[regex]::Matches($log,'SURFACE_REVIEW camera').Count
 $ok=$p.ExitCode -eq 0 -and -not $bad -and $stale.Count -eq 0 -and $cameras -eq 14
 @{ok=$ok;exit_code=$p.ExitCode;started=$started.ToUniversalTime().ToString('o');shader_validation_passed=(-not $bad);missing_or_stale=$stale;camera_commands=$cameras;performance_verified=$false;gpu_timeout_warnings=([regex]::Matches($log,'GPU timeout:').Count);capture='Standalone game; fixed views and sampled lateral camera sweep';plan=$plan} | ConvertTo-Json -Depth 10 | Set-Content "$qa/process.json"
 if(-not $ok){throw 'Standalone parallax capture failed; inspect process.json'}
 Write-Output 'Standalone parallax review passed'
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

param([switch]$Warmth,[switch]$Canopy)
$ErrorActionPreference='Stop'
Set-Location C:/GrandTour
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal occupied'}
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Unreal reserved'}
 if($Canopy){python Art/tools/prepare_palette_capture.py --canopy}elseif($Warmth){python Art/tools/prepare_palette_capture.py --warmth}else{python Art/tools/prepare_palette_capture.py}
 if($LASTEXITCODE -ne 0){throw 'Capture plan failed'}
 $qa=if($Canopy){'C:/GrandTour/Saved/LidarAuthoringQA/CanopyInterior/Capture'}elseif($Warmth){'C:/GrandTour/Saved/LidarAuthoringQA/PaletteWarmth/Capture'}else{'C:/GrandTour/Saved/LidarAuthoringQA/PaletteRefinement/Capture'};$plan=Get-Content "$qa/plan.json" -Raw | ConvertFrom-Json
 $initial=(@($plan.quality)+@('EnableCheats','ShowHUD','DisableAllScreenMessages','r.MotionBlurQuality 0','t.IdleWhenNotForeground 0',('CsvProfile FRAMES='+$plan.frames))) -join ','
 $launch=@('C:/GrandTour/GrandTour.uproject','/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy','-game','-windowed','-ResX=1600','-ResY=900','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12',('-ExecCmds="'+$initial+'"'),'-ExitAfterCsvProfiling',('-csvExecCmds="'+($plan.commands -join ',')+'"'),'-abslog=C:/GrandTour/Saved/Logs/PaletteRefinement-Capture.log')
 $started=Get-Date;$p=Start-Process 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $launch -WindowStyle Hidden -PassThru
 $null=$p.Handle;$p.WaitForExit();$log=Get-Content Saved/Logs/PaletteRefinement-Capture.log -Raw
 $bad=$log -match 'missing usage flag|Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error'
 $cameraInterrupted=$log -match 'AGTPlayerController: out of the car'
 $stale=@($plan.images | Where-Object {$f=Get-Item -LiteralPath "$qa/$_" -ErrorAction SilentlyContinue; -not $f -or $f.LastWriteTime -lt $started})
 $switches=[regex]::Matches($log,$(if($Canopy){'CANOPY_DEPTH_REVIEW strength='}else{'DISTANCE_STYLE preset='})).Count
 $ok=$p.ExitCode -eq 0 -and -not $bad -and -not $cameraInterrupted -and $stale.Count -eq 0 -and $switches -eq $plan.images.Count
 @{ok=$ok;exit_code=$p.ExitCode;shader_validation_passed=(-not $bad);camera_interrupted=$cameraInterrupted;missing_or_stale=$stale;review_switches=$switches;performance_verified=$false;plan=$plan} | ConvertTo-Json -Depth 10 | Set-Content "$qa/process.json"
 if(-not $ok){throw 'Palette capture failed; inspect process.json'}
 Write-Output 'Palette refinement capture passed'
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

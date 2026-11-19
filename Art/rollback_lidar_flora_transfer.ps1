$ErrorActionPreference='Stop'
$root='C:/GrandTour'
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Renderer slot reserved'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue){throw 'Close the renderer before restoring the map'}
 $baseline=Get-Content "$root/Art/Export/LidarFloraTransfer/baseline.json" -Raw | ConvertFrom-Json
 $installed=Get-Content "$root/Art/Export/LidarFloraTransfer/install-report.json" -Raw | ConvertFrom-Json
 $target=[IO.Path]::GetFullPath((Join-Path $root $baseline.map))
 if($target -ne 'C:\GrandTour\Content\GrandTour\ArtTests\LidarStudy\L_LidarStudy.umap'){throw 'Unexpected recovery destination'}
 $original=$baseline.hashes.($baseline.map)
 if((Get-FileHash -LiteralPath $baseline.backup -Algorithm SHA256).Hash.ToLowerInvariant() -ne $original){throw 'Recovery copy does not match the baseline'}
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $installed.saved_map_sha256){throw 'The map changed after this transfer; inspect later work before restoring'}
 Copy-Item -LiteralPath $baseline.backup -Destination $target
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $original){throw 'Restore verification failed'}
 Write-Output 'Original LiDAR study restored. Source assets and other maps were untouched.'
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}

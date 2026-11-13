param([switch]$AllowGame)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# MR2 (2026-10-08): -AllowGame runs these CPU tests with a game open (the plan's rule); an editor still refuses.
if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'An editor is running'}
if(-not $AllowGame -and (Get-Process GoW,GoWR,FarCry6 -ErrorAction SilentlyContinue)){throw 'A game is running (-AllowGame runs anyway)'}
$log=Join-Path $root 'Saved/Logs/mud_shape_test.log'
# LM1: every GrandTour.Mud test (SoftShoulders, Settle, and whatever the next stage adds), each judged by its own result.
# LM3a: and every GrandTour.Snow test (Compact), in the same run.
$argsList=@(('"'+$root+'\GrandTour.uproject"'),'-NullRHI','-Unattended','-NoSplash','-NoSound','-NoP4','-ExecCmds="Automation RunTests GrandTour.Mud+GrandTour.Snow+GrandTour.Gravel"','-TestExit="Automation Test Queue Empty"',('-abslog="'+$log+'"'))
$started=Get-Date
$p=Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if($p.ExitCode -ne 0 -or (Get-Item $log).LastWriteTime -lt $started){throw "Mud shape test failed: exit $($p.ExitCode)"}
Select-String -Path $log -Pattern 'cross-step|Settle: |Lumps: |Throw: |Variety: |Variants: |Snow: |Carry: |CarMud: |MuddyWater: |SoftSpots: |Chunks: |Gravel: |PreChurn: ' | ForEach-Object { $_.Line -replace '^.*?(Settle: |Lumps: |Throw: |Variety: |Variants: |Snow: |CarMud: |Carry: |MuddyWater: |SoftSpots: |Chunks: |Gravel: |PreChurn: |max 12)','$1' } | Select-Object -Unique
$results=@(Select-String -Path $log -Pattern 'Test Completed\. Result=\{([^}]*)\}.*Path=\{(GrandTour\.(Mud|Snow|Gravel)\.[^}]*)\}')
$results | ForEach-Object { $_.Line -replace '^.*?(Test Completed)','$1' }
# LM4: and GrandTour.Snow.GoW (the God of War snow rows). LM4c: and GrandTour.Snow.Piles. LM4d: and GrandTour.Snow.Channel.
# LM5b: and GrandTour.Mud.Variants (a row per mud variant). MR1: and GrandTour.Mud.Carry (the carried mud, CPU). MR2: and
# GrandTour.Mud.CarMud (the muddy vehicle's body state, CPU). MR3: and GrandTour.Mud.MuddyWater (the rut pools' turbidity, CPU).
# MR4: and GrandTour.Mud.SoftSpots (the soft spots' field, scales, stroke and switch, CPU). MR5: and GrandTour.Mud.Chunks (the
# chunks' spawn, wheel and impulse breaks, awake cap, a drop in Chaos and the switch). Deformable gravel DG1: and GrandTour.Gravel.Stones
# (the loose stones' placement, the wheel's push, the flick, the windrow heaps and the switches, CPU).
if($results.Count -lt 16){throw "Expected every GrandTour.Mud, GrandTour.Snow and GrandTour.Gravel test to report (SoftShoulders, Settle, Lumps, Throw, Variety, Variants, Carry, CarMud, MuddyWater, SoftSpots, Snow.Compact, Snow.GoW, Snow.Piles, Snow.Channel, Chunks, Gravel.Stones); found $($results.Count)"}
$bad=@($results | Where-Object { $_.Matches[0].Groups[1].Value -ne 'Success' })
if($bad.Count -gt 0){
  Select-String -Path $log -Pattern 'Error:|Expected' | Select-Object -Last 12 | ForEach-Object { $_.Line }
  throw "$($bad.Count) of $($results.Count) GrandTour.Mud/Snow/Gravel test(s) did not succeed"
}
Write-Output "MUD_SHAPE_OK: $($results.Count) GrandTour.Mud, GrandTour.Snow and GrandTour.Gravel tests, all Success"

param([ValidateSet('A','B','C','K')][string]$Mode='A',[double]$Minutes=0,[string]$Off='',[string]$Cmds='',[string]$Tag='',[string]$ExtraArgs='',[ValidateSet('','move','still')][string]$BKind='',[switch]$NoRainCapture,[switch]$Pace,[switch]$AllowGame,[switch]$ParseOnly)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
# VRAM soak (docs/VRAM_SOAK.md): a memory investigation, NO frame-time or cost measurement. Runs Art/Unreal/soak_vram.py in PIE
# (1440x900, the editor's background throttle off, as the mud and snow checks) and logs the RHI / D3D12 memory and object counters
# every 30 s (A, C) or after each capture (B). Meanwhile this wrapper samples, every 30 s, Windows' own view of the editor process:
# GPU Process Memory (dedicated, shared) and the process's private bytes. Then it parses the log into Saved/Logs/soak_vram_<name>.csv.
#   -Mode A  L_MudVariants, the strip's drive repeated (-Minutes, default 10)
#   -Mode B  L_MudVariants, the car parked, 25 HighResShots + 6 buffer dumps as check_mud_variants.py, then a 60 s hold
#            -BKind move: the camera jumps only (no capture); -BKind still: 25 HighResShots from one camera, no dumps
#   -Mode C  L_SnowDrive, its drive repeated (-Minutes, default 5)
#   -Mode K  check_mud_variants.py itself (its pictures and report into Saved/SoakVRAM/K) with the logger every 15 s; the check
#            waits for the GPU each tick on its own (GT_CHECK_PACE, default on; set $env:GT_CHECK_PACE='0' first for an unpaced run)
#   -Off 'gt.Mud.Settle,gt.Mud.Carry'  switches set to 0 for the run (the bisect); -Cmds 'cmd1;cmd2' run once play starts
#   -Pace  every tick waits for the GPU (a 1x1 render target readback), modes A, B and C; a no-op in mode K (the check paces)
#   -NoRainCapture  the rain emitter's occlusion capture off (its tick disabled) for the run
#   -ExtraArgs '-dpcvars=...'  extra editor arguments; -Tag names the log / csv (default the mode); -ParseOnly re-parses a log
$name='soak_vram_'+$(if($Tag){$Tag}else{$Mode})
$log="$root\Saved\Logs\$name.log";$ext="$root\Saved\Logs\$name.external.csv";$csv="$root\Saved\Logs\$name.csv"
if(-not $ParseOnly){
  if(Get-Process UnrealEditor,UnrealEditor-Cmd,GrandTour -ErrorAction SilentlyContinue){throw 'An editor is running'}
  if(-not $AllowGame -and (Get-Process FarCry6,GoW,GoWR -ErrorAction SilentlyContinue)){throw 'A game is running (GoWR, GoW and FarCry6 are checked; -AllowGame runs anyway)'}
  $env:GT_SOAK_MODE=$Mode;$env:GT_SOAK_B=$BKind;$env:GT_SOAK_OFF=$Off;$env:GT_SOAK_CMDS=$Cmds;$env:GT_SOAK_NORAINCAPTURE=$(if($NoRainCapture){'1'}else{''});$env:GT_SOAK_PACE=$(if($Pace){'1'}else{''})
  if($Minutes -gt 0){$env:GT_SOAK_MINUTES="$Minutes"}else{Remove-Item Env:GT_SOAK_MINUTES -ErrorAction SilentlyContinue}
  $argsList=@(('"'+$root+'\GrandTour.uproject"'),'-RenderOffScreen','-dx12','-Unattended','-NoSplash','-NoSound','-GTLookKuwahara=0','-GTNoLoad','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False','-ResX=1440','-ResY=900','-ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100"',('-ExecutePythonScript="'+$root+'\Art\Unreal\soak_vram.py"'),('-abslog="'+$log+'"'))
  if($ExtraArgs){$argsList+=$ExtraArgs}
  $p=[Diagnostics.Process]::new()
  $p.StartInfo.FileName='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
  $p.StartInfo.Arguments=$argsList -join ' '
  $p.StartInfo.UseShellExecute=$false
  $p.StartInfo.CreateNoWindow=$true
  $p.StartInfo.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
  $t0=Get-Date
  if(-not $p.Start()){throw 'Unreal did not start'}
  'elapsed_s,gpu_dedicated_mb,gpu_shared_mb,gpu_committed_mb,private_mb,working_set_mb'|Set-Content $ext -Encoding ascii
  while(-not $p.WaitForExit(30000)){
    # Windows' GPU memory per process (all adapters' entries for this pid summed); the counters exist on WDDM 2+.
    $d=$s=$c=0
    try{$d=((Get-Counter "\GPU Process Memory(pid_$($p.Id)_*)\Dedicated Usage" -ErrorAction Stop).CounterSamples|Measure-Object CookedValue -Sum).Sum/1MB}catch{}
    try{$s=((Get-Counter "\GPU Process Memory(pid_$($p.Id)_*)\Shared Usage" -ErrorAction Stop).CounterSamples|Measure-Object CookedValue -Sum).Sum/1MB}catch{}
    try{$c=((Get-Counter "\GPU Process Memory(pid_$($p.Id)_*)\Total Committed" -ErrorAction Stop).CounterSamples|Measure-Object CookedValue -Sum).Sum/1MB}catch{}
    try{$p.Refresh();$pm=$p.PrivateMemorySize64/1MB;$ws=$p.WorkingSet64/1MB}catch{$pm=$ws=0}
    ('{0:F0},{1:F0},{2:F0},{3:F0},{4:F0},{5:F0}' -f ((Get-Date)-$t0).TotalSeconds,$d,$s,$c,$pm,$ws)|Add-Content $ext -Encoding ascii
  }
  Write-Output ("editor exit {0} after {1:F0} s" -f $p.ExitCode,((Get-Date)-$t0).TotalSeconds)
  $rep=Get-Item $(if($Mode -eq 'K'){"$root\Saved\SoakVRAM\K\drive-report.json"}else{"$root\Saved\SoakVRAM\soak-$Mode-report.json"}) -ErrorAction SilentlyContinue
  if($rep -and $rep.LastWriteTime -ge $t0){$r=Get-Content $rep.FullName -Raw|ConvertFrom-Json;Write-Output ("report ok {0}, viewport {1}, laps {2}, error {3}" -f $r.ok,($r.viewport_size -join 'x'),@($r.laps).Count,$r.error)}else{Write-Output 'no fresh report (crash or timeout)'}
}
# ---- parse: one row per GTSOAK_MARK, the numbers between it and the next mark --------------------------------------------------
$want=[ordered]@{d3d_total='STAT_D3D12MemoryCurrentTotal';rt='STAT_D3D12RenderTargets';uav_tex='STAT_D3D12UAVTextures';tex='STAT_D3D12Textures';uav_buf='STAT_D3D12UAVBuffers';buf='STAT_D3D12Buffer';rt_buf='STAT_D3D12RTBuffers';transient='STAT_D3D12TransientHeaps';
  resv_buf_commit='STAT_ReservedCommittedBufferMemory';resv_buf_uncommit='STAT_ReservedUncommittedBufferMemory';resv_tex_commit='STAT_ReservedCommittedTextureMemory';uav_tex_rhi='STAT_UAVTextureMemory';rt2d_rhi='STAT_RenderTargetMemory2D';tex2d_rhi='STAT_TextureMemory2D';
  structured='STAT_StructuredBufferMemory';byteaddr='STAT_ByteAddressBufferMemory';vb='STAT_VertexBufferMemory';ib='STAT_IndexBufferMemory';ub='STAT_UniformBufferMemory';bindless='STAT_BindlessResourceHeapMemory';
  upload_alloc='STAT_D3D12UploadPoolMemoryAllocated';bufpool_alloc='STAT_D3D12BufferPoolMemoryAllocated';uavbuf_standalone_n='STAT_D3D12UAVBufferStandAloneCount';uavbuf_standalone='STAT_D3D12UAVBufferStandAloneAllocated';
  cmdlists='STAT_D3D12NumCommandLists';cmdallocs='STAT_D3D12NumCommandAllocators';queryheaps='STAT_D3D12NumQueryHeaps';psos='STAT_D3D12NumPSOs'}
$rows=@();$cur=$null;$top=@{};$topTag=$null
foreach($line in [IO.File]::ReadLines($log)){
  if($line -match 'GTSOAK_MARK (\d+) (\S+) t=([\d.]+) frame=(\d+) (\{.*\})'){
    if($cur){$rows+=[pscustomobject]$cur}
    $cur=[ordered]@{n=[int]$Matches[1];tag=$Matches[2];t_s=[double]$Matches[3]};foreach($k in $want.Keys){$cur[$k]=''};$cur['pool_ref']='';$cur['pool_alloc']='';$cur['pool_n']='';$cur['tracked']='';$cur['gt']=$Matches[5];$topTag=$null;continue}
  if($line -match 'GTSOAK_TOP \d+ (\S+)'){$topTag=$Matches[1];$top[$topTag]=@();continue}
  if(-not $cur){continue}
  if($line -match '\s([\d.]+)(MB)?\s+-\s+.*? - (STAT_\w+) - STATGROUP_'){foreach($k in $want.Keys){if($want[$k] -eq $Matches[3]){$cur[$k]=$Matches[1]}}}
  elseif($line -match '\]([\d.]+)MB total, ([\d.]+)MB used, [\d.]+MB unused, (\d+) render targets'){$cur['pool_alloc']=[math]::Round([double]$Matches[1]);$cur['pool_ref']=[math]::Round([double]$Matches[2]);$cur['pool_n']=$Matches[3]}
  elseif($line -match 'Total tracked resource size: ([\d.]+) MB'){$cur['tracked']=[math]::Round([double]$Matches[1],1)}
  elseif($topTag -and $line -match 'Name: (.*) - Type: (\S+) - Size: ([\d.]+) MB - Flags: (.*) - Owner'){$top[$topTag]+=('{0,9:F1} MB  {1}  {2}  [{3}]' -f [double]$Matches[3],$Matches[2],$Matches[1],$Matches[4])}
}
if($cur){$rows+=[pscustomobject]$cur}
$rows|Export-Csv $csv -NoTypeInformation
Write-Output "marks: $($rows.Count) -> $csv"
$rows|Format-Table n,tag,t_s,d3d_total,uav_buf,buf,tex,uav_tex,rt,resv_buf_commit,resv_buf_uncommit,pool_alloc,pool_n,tracked,cmdlists,cmdallocs -AutoSize|Out-String -Width 250|Write-Output
$rows|Select-Object n,tag,gt|Format-Table -AutoSize|Out-String -Width 300|Write-Output
foreach($k in $top.Keys){Write-Output "top: $k";$top[$k]|Select-Object -First 30|Write-Output}
if(Test-Path $ext){Write-Output 'external (Windows GPU Process Memory, MB):';Import-Csv $ext|Format-Table -AutoSize|Out-String -Width 200|Write-Output}

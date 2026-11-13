# Blocks until no Unreal/build process or Benmore profiling reservation is active, polling every
# -PollSeconds, for at most -MaxMinutes. Exit 0 when free, 1 on timeout. Never kills anything.
# Agents call this as its OWN command before every Unreal or UBT run, and only start the run after it exits 0:
#   powershell -NoProfile -File Art/wait_unreal_free.ps1
param([int]$PollSeconds = 60, [int]$MaxMinutes = 45)
function Test-BenmoreProfileReserved {
    $reservation=$null
    $acquired=$false
    try {
        try {$reservation=[Threading.Mutex]::OpenExisting('Local\GrandTour-BenmoreProfiling')}
        catch [Threading.WaitHandleCannotBeOpenedException] {return $false}
        try {$acquired=$reservation.WaitOne(0)}
        catch [Threading.AbandonedMutexException] {$acquired=$true}
        return -not $acquired
    } finally {
        if($acquired){$reservation.ReleaseMutex()}
        if($reservation){$reservation.Dispose()}
    }
}
$deadline = (Get-Date).AddMinutes($MaxMinutes)
while ($true) {
    $p = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor.*|GrandTour.*|UnrealBuildTool|MSBuild|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    $reserved=Test-BenmoreProfileReserved
    if (-not $p.Count -and -not $reserved) { Write-Output 'UNREAL FREE'; exit 0 }
    $list = ($p | ForEach-Object { "$($_.Name)#$($_.ProcessId)" }) -join ', '
    if($reserved){$list+=' [Benmore profiling reservation]'}
    if ((Get-Date) -ge $deadline) { Write-Output "TIMEOUT: still running: $list"; exit 1 }
    Write-Output "$(Get-Date -Format HH:mm:ss) waiting: $list"
    Start-Sleep -Seconds $PollSeconds
}

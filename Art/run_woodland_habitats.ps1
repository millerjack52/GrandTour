[CmdletBinding()]
param([ValidateSet('Prepare','Install','Surface','GroundPaint','Verify')][string]$Stage='Prepare',
      [string]$BackupDirectory,
      [ValidateRange(1,9999)][int]$Revision=1)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$dir=Join-Path $root 'Saved/WoodlandHabitats'
$null=New-Item -Path $dir -ItemType Directory -Force
$map=Join-Path $root 'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
$editor='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
if(Get-Process UnrealEditor*,blender,Wardogs* -ErrorAction SilentlyContinue){throw 'Renderer or game is active.'}
if($Stage -eq 'Install'){
    if(!$BackupDirectory){$BackupDirectory=Join-Path $dir 'Backups'}
    $null=New-Item -Path $BackupDirectory -ItemType Directory -Force
    $hash=(Get-FileHash -LiteralPath $map).Hash
    $copy=Join-Path $BackupDirectory ($hash+'.umap')
    if(!(Test-Path -LiteralPath $copy)){Copy-Item -LiteralPath $map -Destination $copy}
    if((Get-FileHash -LiteralPath $copy).Hash -ne $hash){throw 'Map backup failed checksum.'}
    $env:GT_HABITAT_BACKUP=$copy
}
$env:GT_HABITAT_STAGE=$Stage
$env:GT_HABITAT_REVISION=[string]$Revision
$env:GT_HABITAT_RUN=[guid]::NewGuid().ToString()
$script=Join-Path $PSScriptRoot 'Unreal/woodland_habitats.py'
$log=Join-Path $dir ($Stage+'.log')
$argsList=@(('"'+$root+'/GrandTour.uproject"'),'-run=pythonscript',('-script="'+$script+'"'),
    '-EnablePlugins=PythonScriptPlugin','-unattended','-nop4','-nosplash','-nosound',('-abslog="'+$log+'"'))
$proc=Start-Process $editor -ArgumentList $argsList -WindowStyle Hidden -PassThru -Wait
$receipt=Join-Path $dir ($Stage+'.json')
if(!(Test-Path $receipt)){throw "No receipt from $Stage. See $log"}
$r=Get-Content -Raw -LiteralPath $receipt | ConvertFrom-Json
if($r.run -ne $env:GT_HABITAT_RUN -or !$r.ok -or $proc.ExitCode -ne 0){throw "$Stage failed. $($r.error) See $log"}
if($Stage -eq 'Prepare'){
    & (Join-Path $root 'Saved/Tools/TerrainPython/Scripts/python.exe') (Join-Path $PSScriptRoot 'tools/bake_woodland_habitats.py') --place (Join-Path $PSScriptRoot 'Export/LidarStudy/Place') --out $dir --trees (Join-Path $dir 'canopy.xy')
    if($LASTEXITCODE){throw 'Woodland habitat bake failed.'}
}
Write-Output "$Stage complete. $receipt"

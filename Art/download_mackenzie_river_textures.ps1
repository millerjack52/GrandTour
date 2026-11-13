# Original CC0 Poly Haven files; no edits to source pixels.
$ErrorActionPreference='Stop'
$folder=Join-Path $PSScriptRoot 'Textures/MackenzieRiver'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$asset='ganges_river_pebbles'
$api=Invoke-RestMethod ('https://api.polyhaven.com/files/'+$asset)
$records=@()
foreach($pair in @(@('Diffuse','jpg'),@('nor_dx','jpg'),@('Displacement','png'),@('Rough','jpg'),@('AO','jpg'))) {
    $entry=$api.($pair[0]).'2k'.($pair[1])
    $file=Join-Path $folder ([IO.Path]::GetFileName($entry.url))
    if(-not (Test-Path -LiteralPath $file)) {Invoke-WebRequest -Uri $entry.url -OutFile $file}
    $hash=(Get-FileHash -LiteralPath $file -Algorithm MD5).Hash.ToLower()
    if($hash -ne $entry.md5) {throw ('Source hash mismatch: '+$file)}
    $records+=@{kind=$pair[0];file=$file;url=$entry.url;md5=$hash}
}
@{asset=$asset;source='https://polyhaven.com/a/ganges_river_pebbles';license='CC0';author='Amal Kumar';use='Material source; mineral palette adjusted in shader. Not a New Zealand location scan.';files=$records} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'source-manifest.json')
$records | Select-Object kind,md5

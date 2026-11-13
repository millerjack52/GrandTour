# Rebuild L_MudVariants with the approved landscape soil response.
# Run Art/wait_unreal_free.ps1 as its own command before invoking this wrapper.
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'mud_variants_response.ps1') -Mode Setup

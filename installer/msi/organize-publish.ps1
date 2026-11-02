# Self-contained publish: плоский bin (как 2.0.2) — все DLL рядом с BadAgent.exe, без ms/lib.

param(
    [Parameter(Mandatory = $true)]
    [string]$BinDir
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $BinDir)) {
    throw "organize-publish: bin dir not found: $BinDir"
}

Write-Host "organize-publish: flat bin (no ms/lib split) -> $BinDir"

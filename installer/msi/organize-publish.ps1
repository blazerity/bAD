# Раскладка publish\bin после dotnet publish (self-contained):
#   BadAgent.exe / BadAgent.dll / *.json / uninstall.cmd / native host — в корне bin\
#   Microsoft.* / System.* / netstandard (managed) — в bin\ms\
#   остальные NuGet DLL (Serilog и т.п.) — в bin\lib\
# coreclr/hostfxr/hostpolicy/clrjit и пр. native — остаются в корне.

param(
    [Parameter(Mandatory = $true)]
    [string]$BinDir
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $BinDir)) {
    throw "organize-publish: bin dir not found: $BinDir"
}

$ms = Join-Path $BinDir "ms"
$lib = Join-Path $BinDir "lib"
New-Item -ItemType Directory -Force -Path $ms, $lib | Out-Null

$keepNames = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]@("BadAgent.dll", "BadAgent.exe"),
    [StringComparer]::OrdinalIgnoreCase
)

function Test-MsAssembly([string]$name) {
    return $name -match '^(Microsoft\.|System\.|netstandard|WindowsBase|PresentationFramework|PresentationCore|WindowsForms)'
}

Get-ChildItem -LiteralPath $BinDir -File -Filter "*.dll" | ForEach-Object {
    if ($keepNames.Contains($_.Name)) {
        return
    }
    # Нативные (без managed metadata) лучше не трогать — эвристика по имени
    if ($_.Name -match '^(coreclr|hostfxr|hostpolicy|clrjit|mscordaccore|mscordbi|createdump)') {
        return
    }
    $destDir = if (Test-MsAssembly $_.Name) { $ms } else { $lib }
    $dest = Join-Path $destDir $_.Name
    if (Test-Path -LiteralPath $dest) {
        Remove-Item -LiteralPath $dest -Force
    }
    Move-Item -LiteralPath $_.FullName -Destination $dest -Force
}

# Культурные сателлиты (ru\*.dll и т.п.) — в ms\<culture>\
Get-ChildItem -LiteralPath $BinDir -Directory | Where-Object {
    $_.Name -notin @("ms", "lib", "runtimes") -and $_.Name.Length -le 5
} | ForEach-Object {
    $cultureDir = $_
    $hasDll = Get-ChildItem -LiteralPath $cultureDir.FullName -Filter "*.dll" -ErrorAction SilentlyContinue
    if (-not $hasDll) { return }
    $targetCulture = Join-Path $ms $cultureDir.Name
    New-Item -ItemType Directory -Force -Path $targetCulture | Out-Null
    Get-ChildItem -LiteralPath $cultureDir.FullName -File | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination (Join-Path $targetCulture $_.Name) -Force
    }
    Remove-Item -LiteralPath $cultureDir.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "organize-publish: ok -> $BinDir (ms/ + lib/)"

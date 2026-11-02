# Удалить пустые bin\ms и bin\lib после апгрейда с 2.1.1–2.1.3 (сироты, не часть нового плоского bin).

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir
)

$ErrorActionPreference = "Stop"

function Write-CleanupOrphanLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try { Write-Host $line } catch { }
    try {
        $logDir = Join-Path $env:ProgramData "blazerity\bAD\logs"
        if (-not (Test-Path -LiteralPath $logDir)) {
            New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        }
        Add-Content -Path (Join-Path $logDir "msi-install.log") -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

function Remove-EmptyTree([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $files = @(Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue)
    if ($files.Count -gt 0) {
        Write-CleanupOrphanLog "INFO skip non-empty orphan $Path"
        return
    }
    Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
    Write-CleanupOrphanLog "INFO removed empty orphan $Path"
}

$root = $InstallDir.TrimEnd('\')
$bin = Join-Path $root "bin"
Write-CleanupOrphanLog "INFO cleanup-orphan-bin-dirs InstallDir=$root"

foreach ($name in @("ms", "lib")) {
    Remove-EmptyTree -Path (Join-Path $bin $name)
}

Write-CleanupOrphanLog "OK cleanup-orphan-bin-dirs complete"
exit 0

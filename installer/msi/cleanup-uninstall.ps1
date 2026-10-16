# Полный uninstall (не MajorUpgrade): убрать enrollment leftovers из ProgramData.
# Служба и Program Files снимает WiX ServiceControl / Component.
# Upgrade сохраняет config (этот скрипт не вызывается при UPGRADINGPRODUCTCODE).
# Лог best-effort: %TEMP%\bad-msi-cleanup.log (ProgramData logs как раз удаляем).

$ErrorActionPreference = "Continue"

function Write-CleanupLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try { Write-Host $line } catch { }
    try {
        $p = Join-Path $env:TEMP "bad-msi-cleanup.log"
        Add-Content -Path $p -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

try {
    . (Join-Path $PSScriptRoot "bad-paths.ps1")
} catch {
    Write-CleanupLog "ERROR BAD_MSI_101 cannot load bad-paths.ps1: $($_.Exception.Message)"
    exit 0
}

$dir = $BadProgramData
Write-CleanupLog "INFO cleanup-uninstall start dir=$dir"

if (-not (Test-Path $dir)) {
    Write-CleanupLog "OK BAD_MSI_100 nothing to clean"
    exit 0
}

# Секреты и очередь — обязательно
Remove-Item -Force -ErrorAction SilentlyContinue $BadConfigPath
Remove-Item -Force -ErrorAction SilentlyContinue "$BadConfigPath.tmp"
if (Test-Path $BadQueueDir) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $BadQueueDir
}

# На случай обрыва install: временный Setup с enrollment token
Remove-Item -Path "HKLM:\SOFTWARE\blazerity\bAD\Setup" -Recurse -Force -ErrorAction SilentlyContinue

# Логи — best-effort (могут быть locked)
if (Test-Path $BadLogsDir) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $BadLogsDir
}

# Если каталог пуст — убрать его и родителя blazerity при пустоте
try {
    if ((Test-Path $dir) -and -not (Get-ChildItem -Force $dir -ErrorAction SilentlyContinue)) {
        Remove-Item -Force -ErrorAction SilentlyContinue $dir
    }
    $parent = $BadProgramDataParent
    if ((Test-Path $parent) -and -not (Get-ChildItem -Force $parent -ErrorAction SilentlyContinue)) {
        Remove-Item -Force -ErrorAction SilentlyContinue $parent
    }
} catch {
    Write-CleanupLog "WARN cleanup dirs: $($_.Exception.Message)"
}

Write-CleanupLog "OK BAD_MSI_100 cleanup-uninstall complete"
exit 0

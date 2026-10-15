# Полный uninstall (не MajorUpgrade): убрать enrollment leftovers из ProgramData.
# Служба и Program Files снимает WiX ServiceControl / Component.
# Upgrade сохраняет config (этот скрипт не вызывается при UPGRADINGPRODUCTCODE).

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "bad-paths.ps1")
$dir = $BadProgramData

if (-not (Test-Path $dir)) {
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
    # ignore
}

exit 0

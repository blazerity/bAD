# Полный uninstall (не MajorUpgrade): убрать enrollment leftovers из ProgramData.
# Служба и Program Files снимает WiX ServiceControl / Component.
# Upgrade сохраняет config (этот скрипт не вызывается при UPGRADINGPRODUCTCODE).

$ErrorActionPreference = "Continue"
$dir = Join-Path $env:ProgramData "blazerity\bAD"

if (-not (Test-Path $dir)) {
    exit 0
}

$config = Join-Path $dir "config.json"
$queue = Join-Path $dir "queue"
$logs = Join-Path $dir "logs"

# Секреты и очередь — обязательно
Remove-Item -Force -ErrorAction SilentlyContinue $config
Remove-Item -Force -ErrorAction SilentlyContinue "$config.tmp"
if (Test-Path $queue) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $queue
}

# Логи — best-effort (могут быть locked)
if (Test-Path $logs) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $logs
}

# Если каталог пуст — убрать его и родителя blazerity при пустоте
try {
    if ((Test-Path $dir) -and -not (Get-ChildItem -Force $dir -ErrorAction SilentlyContinue)) {
        Remove-Item -Force -ErrorAction SilentlyContinue $dir
    }
    $parent = Join-Path $env:ProgramData "blazerity"
    if ((Test-Path $parent) -and -not (Get-ChildItem -Force $parent -ErrorAction SilentlyContinue)) {
        Remove-Item -Force -ErrorAction SilentlyContinue $parent
    }
} catch {
    # ignore
}

exit 0

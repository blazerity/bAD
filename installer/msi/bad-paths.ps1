# Единые пути ProgramData для write-config / cleanup-uninstall.
# Источник истины в агенте: ConfigStore.ProgramDataDir + OfflineQueue.QueueDir.
$BadProgramData = Join-Path $env:ProgramData "blazerity\bAD"
$BadConfigPath = Join-Path $BadProgramData "config.json"
$BadQueueDir = Join-Path $BadProgramData "queue"
$BadLogsDir = Join-Path $BadProgramData "logs"
$BadProgramDataParent = Join-Path $env:ProgramData "blazerity"

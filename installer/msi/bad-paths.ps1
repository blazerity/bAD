# Единые пути ProgramData для write-config / cleanup-uninstall.
# Источник истины в агенте: ConfigStore.ProgramDataDir + OfflineQueue.QueueDir.
$BadProgramData = Join-Path $env:ProgramData "blazerity\bADagent"
$BadConfigPath = Join-Path $BadProgramData "config.json"
$BadQueueDir = Join-Path $BadProgramData "queue"
$BadLogsDir = Join-Path $BadProgramData "logs"
$BadProgramDataParent = Join-Path $env:ProgramData "blazerity"

function Get-BadAgentInstallDir {
    param(
        [string]$FromArg = ""
    )
    if (-not [string]::IsNullOrWhiteSpace($FromArg)) {
        return $FromArg.TrimEnd('\')
    }
    try {
        $v = (Get-ItemProperty -Path "HKLM:\SOFTWARE\blazerity\bADagent" -Name InstallDir -ErrorAction Stop).InstallDir
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            return $v.TrimEnd('\')
        }
    } catch { }
    $pf = ${env:ProgramFiles}
    if ([string]::IsNullOrWhiteSpace($pf)) { $pf = "C:\Program Files" }
    return (Join-Path (Join-Path $pf "blazerity") "bADagent")
}

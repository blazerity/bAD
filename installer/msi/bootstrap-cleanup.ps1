# Второй заход (BADBOOTSTRAP=1): удалить задачу bAD-bootstrap и копию MSI. Ошибки не валят установку.

$ErrorActionPreference = "SilentlyContinue"

function Write-CleanupLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try {
        $logDir = Join-Path $env:ProgramData "blazerity\bADagent\logs"
        New-Item -ItemType Directory -Force -Path $logDir -ErrorAction SilentlyContinue | Out-Null
        Add-Content -Path (Join-Path $logDir "msi-install.log") -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

Write-CleanupLog "INFO bootstrap-cleanup start"

schtasks.exe /Delete /TN "bAD-bootstrap" /F 2>$null | Out-Null
Unregister-ScheduledTask -TaskName "bAD-bootstrap" -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

$copy = Join-Path (Join-Path (Join-Path $env:ProgramData "blazerity\bADagent") "updates") "bad-agent-bootstrap.msi"
if (Test-Path -LiteralPath $copy) {
    Remove-Item -LiteralPath $copy -Force -ErrorAction SilentlyContinue
    Write-CleanupLog "INFO bootstrap-cleanup removed $copy"
}

Write-CleanupLog "OK bootstrap-cleanup complete"
exit 0

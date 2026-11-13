# Остановить badagent и дождаться выхода BadAgent.exe до RemoveExistingProducts (MajorUpgrade).
# Deferred install, LocalSystem. InstallDir — из argv или HKLM\SOFTWARE\blazerity\bAD\InstallDir.

param(
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "bad-paths.ps1")

function Write-StopLog {
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

function Test-ServiceExists([string]$Name) {
    try {
        $null = Get-Service -Name $Name -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

$root = Get-BadAgentInstallDir -FromArg $InstallDir
$exe = Join-Path (Join-Path $root "bin") "BadAgent.exe"
Write-StopLog "INFO stop-agent-before-upgrade InstallDir=$root"

if (-not (Test-ServiceExists -Name "badagent")) {
    Write-StopLog "OK stop-agent-before-upgrade (service badagent not installed)"
    exit 0
}

try {
    if (Test-Path -LiteralPath $exe) {
        Write-StopLog "INFO stopping via $exe service stop"
        & $exe service stop
        if ($LASTEXITCODE -ne 0) {
            Write-StopLog "ERROR BAD_MSI_110 BadAgent.exe service stop exit $LASTEXITCODE"
            exit 110
        }
    } else {
        Write-StopLog "INFO stopping via Stop-Service badagent (exe missing)"
        Stop-Service -Name "badagent" -Force -ErrorAction Stop
    }
} catch {
    Write-StopLog "ERROR BAD_MSI_110 stop service: $($_.Exception.Message)"
    exit 110
}

$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
    $procs = @(Get-Process -Name "BadAgent" -ErrorAction SilentlyContinue)
    if ($procs.Count -eq 0) {
        Write-StopLog "OK stop-agent-before-upgrade complete"
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

Write-StopLog "ERROR BAD_MSI_111 BadAgent.exe still running after timeout"
exit 111

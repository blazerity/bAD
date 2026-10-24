# Upgrade с MSI <2.0: служба BlazerityAssetDiscovery, PF\bAD, запись в Machine PATH.
# Deferred install (в т.ч. MajorUpgrade / self-update msiexec). Не при uninstall.

$ErrorActionPreference = "Continue"

function Write-MigrateLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try { Write-Host $line } catch { }
    try {
        $logDir = Join-Path $env:ProgramData "blazerity\bAD\logs"
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        }
        Add-Content -Path (Join-Path $logDir "msi-install.log") -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

function Remove-LegacyService {
    param([string]$Name)
    try {
        $q = & sc.exe query $Name 2>&1
        if ($LASTEXITCODE -ne 0) {
            return
        }
        Write-MigrateLog "INFO stopping legacy service $Name"
        try { Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue } catch { }
        Start-Sleep -Seconds 2
        Write-MigrateLog "INFO deleting legacy service $Name"
        & sc.exe delete $Name | Out-Null
    } catch {
        Write-MigrateLog "WARN service $Name : $($_.Exception.Message)"
    }
}

Remove-LegacyService -Name "BlazerityAssetDiscovery"

$pf = ${env:ProgramFiles}
if ([string]::IsNullOrWhiteSpace($pf)) {
    $pf = "C:\Program Files"
}
$legacyInstall = Join-Path (Join-Path $pf "blazerity") "bAD"
if (Test-Path -LiteralPath $legacyInstall) {
    Write-MigrateLog "INFO removing legacy install dir $legacyInstall"
    try {
        Remove-Item -LiteralPath $legacyInstall -Recurse -Force -ErrorAction Stop
    } catch {
        Write-MigrateLog "WARN legacy install dir: $($_.Exception.Message)"
    }
}

try {
    $current = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($current) {
        $parts = $current -split ';' | Where-Object { $_ -and ($_ -ne '') }
        $legacyNorm = $legacyInstall.TrimEnd('\').ToLowerInvariant()
        $filtered = @($parts | Where-Object {
            $p = $_.TrimEnd('\').ToLowerInvariant()
            $p -ne $legacyNorm -and $p -notlike '*\blazerity\bAD'
        })
        if ($filtered.Count -lt $parts.Count) {
            $newPath = ($filtered -join ';').TrimEnd(';')
            [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
            Write-MigrateLog "INFO removed legacy path from Machine PATH"
        }
    }
} catch {
    Write-MigrateLog "WARN PATH cleanup: $($_.Exception.Message)"
}

Write-MigrateLog "OK migrate-legacy-install complete"
exit 0

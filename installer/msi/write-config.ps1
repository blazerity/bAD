# config.json из HKLM …\Setup (не argv). Setup удаляется после чтения. См. Product.wxs SEC-011.
#
# Коды ошибок (пишутся в лог и stderr для WixQuietExec / диалога MSI):
#   BAD_MSI_000 — успех
#   BAD_MSI_001 — не найден bad-paths.ps1 рядом со скриптом
#   BAD_MSI_002 — не удалось создать ProgramData / logs
#   BAD_MSI_003 — ошибка чтения или записи config.json
#   BAD_MSI_004 — ошибка ACL на config.json
#   BAD_MSI_005 — непредвиденная ошибка write-config

param()

$ErrorActionPreference = "Stop"

$script:InstallLog = $null
$script:ErrorFile = $null

function Write-BadMsiLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try { Write-Host $line } catch { }
    if ($script:InstallLog) {
        try {
            Add-Content -Path $script:InstallLog -Value $line -Encoding UTF8
        } catch { }
    }
}

function Fail-BadMsi {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Message,
        [int]$ExitCode = 1
    )
    Write-BadMsiLog "ERROR $Code $Message"
    if ($script:ErrorFile) {
        try {
            Set-Content -Path $script:ErrorFile -Value (@($Code, $Message) -join "`n") -Encoding UTF8
        } catch { }
    }
    try {
        [Console]::Error.WriteLine("bAD MSI ${Code}: $Message")
    } catch {
        Write-Error "bAD MSI ${Code}: $Message" -ErrorAction Continue
    }
    exit $ExitCode
}

try {
    $pathsFile = Join-Path $PSScriptRoot "bad-paths.ps1"
    if (-not (Test-Path -LiteralPath $pathsFile)) {
        Fail-BadMsi -Code "BAD_MSI_001" -Message "bad-paths.ps1 not found at $pathsFile" -ExitCode 1
    }
    . $pathsFile

    try {
        New-Item -ItemType Directory -Force -Path $BadProgramData | Out-Null
        New-Item -ItemType Directory -Force -Path $BadLogsDir | Out-Null
    } catch {
        Fail-BadMsi -Code "BAD_MSI_002" -Message "Cannot create ProgramData dirs: $($_.Exception.Message)" -ExitCode 2
    }

    $script:InstallLog = Join-Path $BadLogsDir "msi-install.log"
    $script:ErrorFile = Join-Path $BadLogsDir "msi-ca-error.txt"
    Write-BadMsiLog "INFO write-config start ProductData=$BadProgramData"

    $setupKey = "HKLM:\SOFTWARE\blazerity\bAD\Setup"
    $ServerUrl = ""
    $EnrollmentToken = ""
    if (Test-Path $setupKey) {
        try {
            $props = Get-ItemProperty -Path $setupKey -ErrorAction Stop
            if ($props.PSObject.Properties.Name -contains "ServerUrl") {
                $ServerUrl = [string]$props.ServerUrl
            }
            if ($props.PSObject.Properties.Name -contains "EnrollmentToken") {
                $EnrollmentToken = [string]$props.EnrollmentToken
            }
            Write-BadMsiLog "INFO Setup registry present server_url_set=$([bool]$ServerUrl) token_set=$([bool]$EnrollmentToken)"
        } catch {
            Write-BadMsiLog "WARN Setup registry read failed: $($_.Exception.Message)"
        }
    } else {
        Write-BadMsiLog "INFO Setup registry absent (upgrade without new properties)"
    }

    $configPath = $BadConfigPath
    $existing = $null
    if (Test-Path $configPath) {
        try {
            $existing = Get-Content -Raw -Path $configPath | ConvertFrom-Json
            Write-BadMsiLog "INFO existing config.json loaded"
        } catch {
            Write-BadMsiLog "WARN existing config.json unreadable, recreating: $($_.Exception.Message)"
            $existing = $null
        }
    }

    $obj = [ordered]@{
        server_url                 = if ($ServerUrl) { $ServerUrl.TrimEnd('/') } elseif ($existing) { $existing.server_url } else { "" }
        inventory_interval_hours   = 6
        heartbeat_interval_minutes = 15
    }

    # Сохранять api_key / device_id при апгрейдах
    if ($existing -and $existing.api_key) {
        $obj.api_key = $existing.api_key
    }
    if ($existing -and $existing.device_id) {
        $obj.device_id = $existing.device_id
    }

    # Ставить enrollment token только если ещё нет API key (первая установка / re-enroll)
    if (-not $obj.api_key -and $EnrollmentToken) {
        $obj.enrollment_token = $EnrollmentToken
    }

    try {
        $tmp = "$configPath.tmp"
        ($obj | ConvertTo-Json -Depth 5) | Set-Content -Path $tmp -Encoding UTF8
        Move-Item -Force -Path $tmp -Destination $configPath
        Write-BadMsiLog "INFO config.json written"
    } catch {
        Fail-BadMsi -Code "BAD_MSI_003" -Message "Cannot write config.json: $($_.Exception.Message)" -ExitCode 3
    }

    # ACL через SID (локализова. BUILTIN\Administrators ломает RU/др. Windows → 1722)
    try {
        $adminSid = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-544")
        $systemSid = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-18")
        $adminRef = $adminSid.Translate([System.Security.Principal.NTAccount])
        $systemRef = $systemSid.Translate([System.Security.Principal.NTAccount])

        $acl = Get-Acl -LiteralPath $configPath
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($ace in @($acl.Access)) {
            [void]$acl.RemoveAccessRule($ace)
        }
        $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule(
            $adminRef, "FullControl", "Allow")))
        $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule(
            $systemRef, "FullControl", "Allow")))
        Set-Acl -LiteralPath $configPath -AclObject $acl
        Write-BadMsiLog "INFO ACL set Administrators+SYSTEM via SID"
    } catch {
        Fail-BadMsi -Code "BAD_MSI_004" -Message "Cannot set config.json ACL: $($_.Exception.Message)" -ExitCode 4
    }

    # Убрать plaintext token из registry после применения
    if (Test-Path $setupKey) {
        Remove-Item -Path $setupKey -Recurse -Force -ErrorAction SilentlyContinue
        Write-BadMsiLog "INFO Setup registry key removed"
    }

    if (Test-Path -LiteralPath $script:ErrorFile) {
        Remove-Item -Force -LiteralPath $script:ErrorFile -ErrorAction SilentlyContinue
    }
    Write-BadMsiLog "OK BAD_MSI_000 write-config complete"
    exit 0
} catch {
    Fail-BadMsi -Code "BAD_MSI_005" -Message $_.Exception.Message -ExitCode 5
}

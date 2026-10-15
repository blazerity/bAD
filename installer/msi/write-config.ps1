# Пишет config.json из HKLM\SOFTWARE\blazerity\bAD\Setup (WiX RegistryValue),
# не из argv — чтобы enrollment token не попадал в командную строку deferred CA (SEC-011).
# Setup-ключи удаляются после чтения.

param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "bad-paths.ps1")
$dir = $BadProgramData
New-Item -ItemType Directory -Force -Path $dir | Out-Null
New-Item -ItemType Directory -Force -Path $BadLogsDir | Out-Null

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
    } catch {
        # нет Setup — upgrade без новых свойств
    }
}

$configPath = $BadConfigPath
$existing = $null
if (Test-Path $configPath) {
    try {
        $existing = Get-Content -Raw -Path $configPath | ConvertFrom-Json
    } catch {
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

$tmp = "$configPath.tmp"
($obj | ConvertTo-Json -Depth 5) | Set-Content -Path $tmp -Encoding UTF8
Move-Item -Force -Path $tmp -Destination $configPath

# ACL: только Administrators + SYSTEM
$acl = Get-Acl $configPath
$acl.SetAccessRuleProtection($true, $false)
$rules = @(
    New-Object System.Security.AccessControl.FileSystemAccessRule("BUILTIN\Administrators", "FullControl", "Allow"),
    New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\SYSTEM", "FullControl", "Allow")
)
$acl.Access | ForEach-Object { [void]$acl.RemoveAccessRule($_) }
foreach ($r in $rules) { $acl.AddAccessRule($r) }
Set-Acl -Path $configPath -AclObject $acl

# Убрать plaintext token из registry после применения
if (Test-Path $setupKey) {
    Remove-Item -Path $setupKey -Recurse -Force -ErrorAction SilentlyContinue
}

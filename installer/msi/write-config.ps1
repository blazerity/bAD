param(
    [string]$ServerUrl = "",
    [string]$EnrollmentToken = ""
)

$ErrorActionPreference = "Stop"
$dir = Join-Path $env:ProgramData "blazerity\bAD"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dir "logs") | Out-Null

$configPath = Join-Path $dir "config.json"
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

# Preserve api_key / device_id across upgrades
if ($existing -and $existing.api_key) {
    $obj.api_key = $existing.api_key
}
if ($existing -and $existing.device_id) {
    $obj.device_id = $existing.device_id
}

# Only set enrollment token when no API key yet (first install / re-enroll)
if (-not $obj.api_key -and $EnrollmentToken) {
    $obj.enrollment_token = $EnrollmentToken
}

$tmp = "$configPath.tmp"
($obj | ConvertTo-Json -Depth 5) | Set-Content -Path $tmp -Encoding UTF8
Move-Item -Force -Path $tmp -Destination $configPath

# ACL: Administrators + SYSTEM only
$acl = Get-Acl $configPath
$acl.SetAccessRuleProtection($true, $false)
$rules = @(
    New-Object System.Security.AccessControl.FileSystemAccessRule("BUILTIN\Administrators", "FullControl", "Allow"),
    New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\SYSTEM", "FullControl", "Allow")
)
$acl.Access | ForEach-Object { [void]$acl.RemoveAccessRule($_) }
foreach ($r in $rules) { $acl.AddAccessRule($r) }
Set-Acl -Path $configPath -AclObject $acl

# Первый заход MajorUpgrade с парка <2.1.5: копия MSI + schtasks bAD-bootstrap (+60s), exit 1602.
# Immediate, LocalSystem. Путь к MSI: аргумент или env BAD_ORIG ([OriginalDatabase]).
# Эталон для publish/scripts; inline CA — EncodedCommand в bootstrap-inline.wxi.

param(
    [Parameter(Mandatory = $false)]
    [string]$OriginalDatabase = $env:BAD_ORIG
)

$ErrorActionPreference = "Stop"
$BootstrapExitCode = 1602
$LegacyMaxVersion = [version]"2.1.4.999"

function Write-BootstrapLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try { Write-Host $line } catch { }
    try {
        $logDir = Join-Path $env:ProgramData "blazerity\bAD\logs"
        New-Item -ItemType Directory -Force -Path $logDir -ErrorAction SilentlyContinue | Out-Null
        Add-Content -Path (Join-Path $logDir "msi-install.log") -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

function Get-InstallDir {
    try {
        $v = (Get-ItemProperty -Path "HKLM:\SOFTWARE\blazerity\bAD" -Name InstallDir -ErrorAction Stop).InstallDir
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            return $v.TrimEnd('\')
        }
    } catch { }
    $pf = ${env:ProgramFiles}
    if ([string]::IsNullOrWhiteSpace($pf)) { $pf = "C:\Program Files" }
    return (Join-Path (Join-Path $pf "blazerity") "bad agent")
}

function Get-InstalledAgentVersion {
    param([string]$Root)
    $exe = Join-Path (Join-Path $Root "bin") "BadAgent.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        return $null
    }
    try {
        return [version]$((Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Trim())
    } catch {
        return $null
    }
}

if ([string]::IsNullOrWhiteSpace($OriginalDatabase) -or -not (Test-Path -LiteralPath $OriginalDatabase)) {
    Write-BootstrapLog "ERROR BAD_MSI_120 OriginalDatabase missing: $OriginalDatabase"
    exit 120
}

$installDir = Get-InstallDir
$installedVer = Get-InstalledAgentVersion -Root $installDir
if ($null -ne $installedVer -and $installedVer -gt $LegacyMaxVersion) {
    Write-BootstrapLog "INFO bootstrap skipped (installed agent $installedVer, detached launcher era)"
    exit 0
}

$updatesDir = Join-Path (Join-Path $env:ProgramData "blazerity\bAD") "updates"
$destMsi = Join-Path $updatesDir "bad-agent-bootstrap.msi"
$logDir = Join-Path (Join-Path $env:ProgramData "blazerity\bAD") "logs"
$bootstrapLog = Join-Path $logDir "msiexec-bootstrap.log"

New-Item -ItemType Directory -Force -Path $updatesDir -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Force -Path $logDir -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath $OriginalDatabase -Destination $destMsi -Force

$t = (Get-Date).AddSeconds(90)
$tr = 'msiexec.exe /i "' + $destMsi + '" /qn /norestart BADBOOTSTRAP=1 REBOOT=ReallySuppress /l*v "' + $bootstrapLog + '"'
& "$env:SystemRoot\System32\schtasks.exe" /Create /TN bAD-bootstrap /TR $tr /SC ONCE /ST $($t.ToString('HH:mm')) /SD $($t.ToString('yyyy/MM/dd')) /RU SYSTEM /RL HIGHEST /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-BootstrapLog "ERROR BAD_MSI_120 schtasks exit $LASTEXITCODE"
    exit 120
}

Write-BootstrapLog "INFO bootstrap scheduled (installed=$installedVer copy=$destMsi at=$t)"
exit $BootstrapExitCode

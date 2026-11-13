# Первый заход MajorUpgrade с парка <2.1.5: копия MSI + schtasks bAD-bootstrap (+90s), exit 0 + VBS UserExit (1602).
# Immediate, LocalSystem. Путь к MSI: $env:BAD_ORIG из WiX [OriginalDatabase] (без cmd set).
# Эталон для publish/scripts; inline CA — EncodedCommand в bootstrap-inline.wxi.

param(
    [Parameter(Mandatory = $false)]
    [string]$OriginalDatabase = $env:BAD_ORIG
)

$ErrorActionPreference = "Stop"
$LegacyMaxVersion = [version]"2.1.4.999"
$MarkerName = ".bootstrap-scheduled"

. (Join-Path $PSScriptRoot "bad-paths.ps1")

function Write-BootstrapLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $Message
    try { Write-Host $line } catch { }
    try {
        $logDir = Join-Path $env:ProgramData "blazerity\bADagent\logs"
        New-Item -ItemType Directory -Force -Path $logDir -ErrorAction SilentlyContinue | Out-Null
        Add-Content -Path (Join-Path $logDir "msi-install.log") -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
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
    Write-BootstrapLog "ERROR BAD_MSI_121 OriginalDatabase missing or not found: '$OriginalDatabase'"
    exit 121
}

$installDir = Get-BadAgentInstallDir
$installedVer = Get-InstalledAgentVersion -Root $installDir
if ($null -ne $installedVer -and $installedVer -gt $LegacyMaxVersion) {
    Write-BootstrapLog "INFO bootstrap skipped (installed agent $installedVer, detached launcher era)"
    exit 0
}

$updatesDir = Join-Path (Join-Path $env:ProgramData "blazerity\bADagent") "updates"
$destMsi = Join-Path $updatesDir "bad-agent-bootstrap.msi"
$logDir = Join-Path (Join-Path $env:ProgramData "blazerity\bADagent") "logs"
$bootstrapLog = Join-Path $logDir "msiexec-bootstrap.log"
$marker = Join-Path $updatesDir $MarkerName

New-Item -ItemType Directory -Force -Path $updatesDir -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Force -Path $logDir -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath $OriginalDatabase -Destination $destMsi -Force

$t = (Get-Date).AddSeconds(90)
$tr = 'msiexec.exe /i "' + $destMsi + '" /qn /norestart BADBOOTSTRAP=1 REBOOT=ReallySuppress /l*v "' + $bootstrapLog + '"'
& "$env:SystemRoot\System32\schtasks.exe" /Create /TN bAD-bootstrap /TR $tr /SC ONCE /ST $($t.ToString('HH:mm')) /SD $($t.ToString('yyyy/MM/dd')) /RU SYSTEM /RL HIGHEST /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-BootstrapLog "ERROR BAD_MSI_122 schtasks /Create exit $LASTEXITCODE"
    exit 122
}

Set-Content -LiteralPath $marker -Value $t.ToString("o") -Encoding UTF8 -Force
Write-BootstrapLog "INFO bootstrap scheduled (installed=$installedVer copy=$destMsi at=$t)"
exit 0

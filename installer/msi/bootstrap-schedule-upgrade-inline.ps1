function L([string]$m) {
    $line = "{0:yyyy-MM-ddTHH:mm:ss.fffzzz} {1}" -f [DateTimeOffset]::Now, $m
    try {
        $d = Join-Path $env:ProgramData 'blazerity\bAD\logs'
        New-Item -ItemType Directory -Force -Path $d -EA SilentlyContinue | Out-Null
        Add-Content (Join-Path $d 'msi-install.log') $line -Encoding UTF8 -EA SilentlyContinue
    } catch { }
}
$ErrorActionPreference = 'Stop'
$OriginalDatabase = $env:BAD_ORIG
if ([string]::IsNullOrWhiteSpace($OriginalDatabase) -or -not (Test-Path -LiteralPath $OriginalDatabase)) {
    L "ERROR BAD_MSI_121 OriginalDatabase missing or not found: '$OriginalDatabase'"
    exit 121
}
$i = $null
try { $i = (Get-ItemProperty 'HKLM:\SOFTWARE\blazerity\bAD' InstallDir -EA Stop).InstallDir.TrimEnd('\') } catch { }
if (-not $i) { $i = Join-Path ${env:ProgramFiles} 'blazerity\bad agent' }
$exe = Join-Path (Join-Path $i 'bin') 'BadAgent.exe'
if (Test-Path -LiteralPath $exe) {
    try {
        $v = [version](Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Trim()
        if ($v -gt [version]'2.1.4.999') { L "INFO bootstrap skipped (installed agent $v)"; exit 0 }
    } catch { }
}
$u = Join-Path (Join-Path $env:ProgramData 'blazerity\bAD') 'updates'
$l = Join-Path (Join-Path $env:ProgramData 'blazerity\bAD') 'logs'
$d = Join-Path $u 'bad-agent-bootstrap.msi'
$bl = Join-Path $l 'msiexec-bootstrap.log'
$marker = Join-Path $u '.bootstrap-scheduled'
New-Item -ItemType Directory -Force -Path $u, $l -EA Stop | Out-Null
Copy-Item -LiteralPath $OriginalDatabase -Destination $d -Force
$t = (Get-Date).AddSeconds(90)
$tr = "msiexec.exe /i `"$d`" /qn /norestart BADBOOTSTRAP=1 REBOOT=ReallySuppress /l*v `"$bl`""
& "$env:SystemRoot\System32\schtasks.exe" /Create /TN bAD-bootstrap /TR $tr /SC ONCE /ST $($t.ToString('HH:mm')) /SD $($t.ToString('yyyy/MM/dd')) /RU SYSTEM /RL HIGHEST /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    L "ERROR BAD_MSI_122 schtasks /Create exit $LASTEXITCODE"
    exit 122
}
Set-Content -LiteralPath $marker -Value $t.ToString('o') -Encoding UTF8 -Force
L "INFO bootstrap scheduled copy=$d at=$t"
exit 0

param([string]$OriginalDatabase = $env:BAD_ORIG)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($OriginalDatabase) -or -not (Test-Path -LiteralPath $OriginalDatabase)) { exit 120 }
$i = $null
try { $i = (Get-ItemProperty 'HKLM:\SOFTWARE\blazerity\bAD' InstallDir -EA Stop).InstallDir.TrimEnd('\') } catch { }
if (-not $i) { $i = Join-Path ${env:ProgramFiles} 'blazerity\bad agent' }
$exe = Join-Path (Join-Path $i 'bin') 'BadAgent.exe'
if (Test-Path -LiteralPath $exe) {
    try {
        $v = [version](Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Trim()
        if ($v -gt [version]'2.1.4.999') { exit 0 }
    } catch { }
}
$u = Join-Path (Join-Path $env:ProgramData 'blazerity\bAD') 'updates'
$l = Join-Path (Join-Path $env:ProgramData 'blazerity\bAD') 'logs'
$d = Join-Path $u 'bad-agent-bootstrap.msi'
$bl = Join-Path $l 'msiexec-bootstrap.log'
New-Item -ItemType Directory -Force -Path $u,$l -EA Stop | Out-Null
Copy-Item -LiteralPath $OriginalDatabase -Destination $d -Force
$t = (Get-Date).AddSeconds(90)
$tr = "msiexec.exe /i `"$d`" /qn /norestart BADBOOTSTRAP=1 REBOOT=ReallySuppress /l*v `"$bl`""
& "$env:SystemRoot\System32\schtasks.exe" /Create /TN bAD-bootstrap /TR $tr /SC ONCE /ST $($t.ToString('HH:mm')) /SD $($t.ToString('yyyy/MM/dd')) /RU SYSTEM /RL HIGHEST /F | Out-Null
if ($LASTEXITCODE -ne 0) { exit 120 }
exit 1602

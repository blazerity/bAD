# bAD Agent MSI (WiX)

Windows-only build. Sources are committed; **Linux CI does not produce an MSI binary**.

GitHub Actions workflow [`.github/workflows/release-msi.yml`](../../.github/workflows/release-msi.yml) builds on `windows-latest` for tag `v*` (or `workflow_dispatch`) and uploads:

- `bad-agent-<semver>.msi`
- `agent-release.json` (`version`, `msi_name`, `sha256`)

to the GitHub Release for that tag.

## Permissions / secrets

| Item | Notes |
|------|--------|
| `contents: write` | Workflow permission to create/update the Release and upload assets |
| `GITHUB_TOKEN` | Default Actions token is enough for this public repo |
| Optional `BAD_GITHUB_TOKEN` on the **server** | Only if the GitHub repo becomes private later |

## Local build (Windows)

```powershell
# 1. Install WiX v5 as a .NET tool (once)
dotnet tool install --global wix --version 5.0.2

# 2. Publish agent
dotnet publish ..\..\agent\src\BadAgent\BadAgent.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:Version=0.8.0 `
  -o .\publish

# 3. Copy write-config.ps1 + bad.cmd shim next to the published exe
Copy-Item .\write-config.ps1 .\publish\
Copy-Item .\bad.cmd .\publish\

# 4. Build MSI (Product.wxs harvests publish\** via <Files>;
#    bad.ico next to Product.wxs → ARPPRODUCTICON; exe icon from ApplicationIcon)
wix build Product.wxs `
  -d AgentPublishDir=publish `
  -d ProductVersion=0.8.0 `
  -o bad-agent-0.8.0.msi
```

## Install / upgrade

```powershell
msiexec /i bad-agent-0.8.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn
```

Optional: add install dir to **Machine PATH** so the `bad` command works from cmd.exe / Win+R (`bad.cmd` shim → `BadAgent.exe`). Default is **off** (`ADDPATH=0` / omitted).

```powershell
msiexec /i bad-agent-0.8.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  ADDPATH=1 `
  /qn
```

Public properties: `SERVERURL`, `ENROLLMENTTOKEN`, `ADDPATH` (optional).

Silent self-update from the agent uses the same MajorUpgrade path. WiX `ServiceControl` stops `BlazerityAssetDiscovery` before file replace and starts it after install. `%ProgramData%\blazerity\bAD\config.json` (API key + device_id) is preserved (`Permanent` ProgramData component). PATH entry from `ADDPATH=1` is removed on uninstall.

## Cut a release

```bash
git tag v0.8.0
git push origin v0.8.0
# → release-msi workflow publishes MSI + agent-release.json
# → on-prem server syncs from GitHub Release (admin sync or background job)
# → agents poll GET /v1/agent/update/check and apply via msiexec
```

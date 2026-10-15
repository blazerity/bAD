# bAD Agent MSI (WiX)

Windows-only build. Sources are committed so CI or a Windows build host can produce `bad-agent-<semver>.msi`.

## Build

```powershell
# 1. Publish agent
dotnet publish ..\..\agent\src\BadAgent\BadAgent.csproj `
  -c Release -r win-x64 --self-contained true `
  -o .\publish

# 2. Copy write-config.ps1 next to the published exe (referenced by Product.wxs)
Copy-Item .\write-config.ps1 .\publish\

# 3. Harvest dependencies (recommended) then build
# heat dir .\publish -cg AgentFiles -gg -sfrag -srd -dr INSTALLFOLDER -out Harvested.wxs
# Or extend Product.wxs File elements for each published artifact.

wix build Product.wxs -d AgentPublishDir=.\publish -o bad-agent-0.2.0.msi
```

## Install

```powershell
msiexec /i bad-agent-0.2.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn
```

Upgrade keeps `%ProgramData%\blazerity\bAD\config.json` (API key + device_id).

# bAD Agent MSI (WiX)

Сборка только на Windows. Исходники в репозитории; **Linux CI MSI-бинарник не выпускает**.

Workflow GitHub Actions [`.github/workflows/release-msi.yml`](../../.github/workflows/release-msi.yml) собирает на `windows-latest` по тегу `v*` (или `workflow_dispatch`) и загружает:

- `bad-agent-<semver>.msi`
- `agent-release.json` (`version`, `msi_name`, `sha256`)

в GitHub Release для этого тега.

## Права / secrets

| Что | Заметки |
|-----|---------|
| `contents: write` | право workflow создавать/обновлять Release и грузить assets |
| `GITHUB_TOKEN` | стандартного токена Actions достаточно для этого public repo |
| Опционально `BAD_GITHUB_TOKEN` на **сервере** | только если репозиторий GitHub позже станет private |

## Локальная сборка (Windows)

```powershell
# 1. Установить WiX v5 как .NET tool (один раз)
dotnet tool install --global wix --version 5.0.2

# 2. Publish агента
dotnet publish ..\..\agent\src\BadAgent\BadAgent.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:Version=0.8.0 `
  -o .\publish

# 3. Скопировать write-config.ps1 + shim bad.cmd рядом с опубликованным exe
Copy-Item .\write-config.ps1 .\publish\
Copy-Item .\bad.cmd .\publish\

# 4. Собрать MSI (Product.wxs harvest'ит publish\** через <Files>;
#    bad.ico рядом с Product.wxs → ARPPRODUCTICON; иконка exe из ApplicationIcon)
wix build Product.wxs `
  -d AgentPublishDir=publish `
  -d ProductVersion=0.8.0 `
  -o bad-agent-0.8.0.msi
```

## Установка / апгрейд

```powershell
msiexec /i bad-agent-0.8.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn
```

Опционально: добавить каталог установки в **Machine PATH**, чтобы команда `bad` работала из cmd.exe / Win+R (`bad.cmd` → `BadAgent.exe`). По умолчанию **выключено** (`ADDPATH=0` / не указано).

```powershell
msiexec /i bad-agent-0.8.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  ADDPATH=1 `
  /qn
```

Public properties: `SERVERURL`, `ENROLLMENTTOKEN`, `ADDPATH` (опционально).

Тихий self-update агента идёт тем же путём MajorUpgrade. WiX `ServiceControl` останавливает `BlazerityAssetDiscovery` перед заменой файлов и запускает после install. `%ProgramData%\blazerity\bAD\config.json` (API key + device_id) сохраняется (компонент ProgramData с `Permanent`). Запись PATH от `ADDPATH=1` снимается при uninstall.

## Вырезать релиз

```bash
git tag v0.8.0
git push origin v0.8.0
# → workflow release-msi публикует MSI + agent-release.json
# → on-prem сервер sync'ит с GitHub Release (admin sync или фоновый job)
# → агенты опрашивают GET /v1/agent/update/check и ставят через msiexec
```

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
| **Authenticode (рекомендуется)** | см. ниже — без сертификата MSI собирается **unsigned** |

### Подпись MSI (Authenticode)

Для нормального релиза нужен **код-сайнинг сертификат владельца** (не генерируется в CI). Workflow подписывает MSI через `signtool`, если заданы secrets:

| Secret | Описание |
|--------|----------|
| `CODE_SIGN_PFX_BASE64` | PFX (PKCS#12) в Base64 |
| `CODE_SIGN_PFX_PASSWORD` | пароль PFX |
| `CODE_SIGN_TIMESTAMP_URL` | опционально; default `http://timestamp.digicert.com` |

Если `CODE_SIGN_PFX_BASE64` пуст — шаг подписи пропускается, артефакт остаётся unsigned (сборка не падает). **Нельзя** подкладывать self-signed «заглушку» вместо боевого cert.

Локально (после сборки MSI):

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /f .\codesign.pfx /p <password> .\bad-agent-0.9.0.msi
```

## Локальная сборка (Windows)

```powershell
# 1. Установить WiX v5 как .NET tool (один раз)
dotnet tool install --global wix --version 5.0.2

# 2. Publish агента
dotnet publish ..\..\agent\src\BadAgent\BadAgent.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:Version=0.9.0 `
  -o .\publish

# 3. Скопировать scripts + shim bad.cmd рядом с опубликованным exe
Copy-Item .\write-config.ps1 .\publish\
Copy-Item .\cleanup-uninstall.ps1 .\publish\
Copy-Item .\bad.cmd .\publish\

# 4. Собрать MSI (Product.wxs harvest'ит publish\** через <Files>;
#    bad.ico рядом с Product.wxs → ARPPRODUCTICON; иконка exe из ApplicationIcon)
wix build Product.wxs `
  -d AgentPublishDir=publish `
  -d ProductVersion=0.9.0 `
  -o bad-agent-0.9.0.msi
```

## Установка / апгрейд

```powershell
msiexec /i bad-agent-0.9.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn
```

Опционально: добавить каталог установки в **Machine PATH**, чтобы команда `bad` работала из cmd.exe / Win+R (`bad.cmd` → `BadAgent.exe`). По умолчанию **выключено** (`ADDPATH=0` / не указано).

```powershell
msiexec /i bad-agent-0.9.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  ADDPATH=1 `
  /qn
```

Public properties: `SERVERURL`, `ENROLLMENTTOKEN`, `ADDPATH` (опционально).

Тихий self-update агента идёт тем же путём MajorUpgrade. WiX `ServiceControl` останавливает `BlazerityAssetDiscovery` перед заменой файлов и запускает после install. `%ProgramData%\blazerity\bAD\config.json` (API key + device_id) сохраняется при **upgrade** (компонент ProgramData с `Permanent`).

### Uninstall

```powershell
msiexec /x bad-agent-0.9.0.msi /qn
```

При полном uninstall (не upgrade): служба Stop+Remove, файлы Program Files снимаются, `cleanup-uninstall.ps1` удаляет `config.json`, `queue\`, `logs\` (enrollment leftovers). Запись PATH от `ADDPATH=1` снимается.

## Вырезать релиз

```bash
git tag v0.9.0
git push origin v0.9.0
# → workflow release-msi публикует MSI (+ Authenticode, если secrets) + agent-release.json
# → on-prem сервер sync'ит с GitHub Release (admin sync или фоновый job)
# → агенты опрашивают GET /v1/agent/update/check и ставят через msiexec
```

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
  /f .\codesign.pfx /p <password> .\bad-agent-0.10.1.msi
```

## Локальная сборка (Windows)

```powershell
# 1. Установить WiX v5 как .NET tool (один раз)
dotnet tool install --global wix --version 5.0.2
wix extension add WixToolset.Util.wixext/5.0.2

# 2. Publish агента
dotnet publish ..\..\agent\src\BadAgent\BadAgent.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:Version=0.10.1 `
  -o .\publish

# 3. Скопировать scripts + shim bad.cmd рядом с опубликованным exe
Copy-Item .\write-config.ps1 .\publish\
Copy-Item .\cleanup-uninstall.ps1 .\publish\
Copy-Item .\bad-paths.ps1 .\publish\
Copy-Item .\bad.cmd .\publish\

# 4. Собрать MSI (Product.wxs harvest'ит publish\** через <Files>,
#    BadAgent.exe — отдельно в компоненте службы; util = WixQuietExec;
#    bad.ico рядом с Product.wxs → ARPPRODUCTICON; иконка exe из ApplicationIcon)
wix build Product.wxs `
  -ext WixToolset.Util.wixext `
  -arch x64 `
  -d AgentPublishDir=publish `
  -d ProductVersion=0.10.1 `
  -o bad-agent-0.10.1.msi
```

## Установка / апгрейд

```powershell
msiexec /i bad-agent-0.10.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn
```

Опционально: добавить каталог установки в **Machine PATH**, чтобы команда `bad` работала из cmd.exe / Win+R (`bad.cmd` → `BadAgent.exe`). По умолчанию **выключено** (`ADDPATH=0` / не указано).

```powershell
msiexec /i bad-agent-0.10.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  ADDPATH=1 `
  /qn
```

Public properties: `SERVERURL`, `ENROLLMENTTOKEN`, `ADDPATH` (опционально).

### Enrollment token и командная строка (SEC-011)

Deferred CA `write-config.ps1` **не** получает `ENROLLMENTTOKEN` / `SERVERURL` в argv. WiX пишет их в `HKLM\SOFTWARE\blazerity\bAD\Setup` через `RegistryValue`; скрипт читает ключ, кладёт token в `config.json` (ACL: Administrators+SYSTEM) и **сразу удаляет** `Setup`.

**Остаточный риск (документируем):**

- Токен всё ещё может быть на **родительской** командной строке оператора: `msiexec /i … ENROLLMENTTOKEN=…` (видно в process list / истории shell на время install).
- При `msiexec /l*v` verbose-лог может содержать значения public properties.
- Кратковременно token лежит в registry `Setup` до конца `write-config` (LocalSystem); при обрыве install ключ снимает `cleanup-uninstall.ps1` / компонент.

Рекомендации: не включать `/l*v` с секретами в долгоживущие шары; после массового деплоя ротировать site enrollment token; предпочитать защищённый канал доставки MSI-команды (Intune/GPO secret, не chat/wiki).

Тихий self-update / pin-downgrade агента идёт через MajorUpgrade (`AllowDowngrades=yes` с 0.10). WiX `ServiceControl` останавливает `BlazerityAssetDiscovery` перед заменой файлов и запускает после install. `%ProgramData%\blazerity\bAD\config.json` (API key + device_id) сохраняется при **upgrade/downgrade** (компонент ProgramData с `Permanent`).

### Логи установки (если MSI падает до старта агента)

Агентский Serilog (`logs\bad-agent-*.log`) появляется **только после** успешного старта службы. Сбой custom action (типичный RU-диалог MSI 1722) логируется раньше:

| Куда | Что |
|------|-----|
| `%ProgramData%\blazerity\bAD\logs\msi-install.log` | шаги `write-config` + коды `BAD_MSI_###` (файл не в Component — часто остаётся после rollback) |
| `%ProgramData%\blazerity\bAD\logs\msi-ca-error.txt` | последний код/текст при ошибке CA |
| `%TEMP%\MSI*.log` | msiexec verbose (`MsiLogging=voicewarmupx` в MSI; плюс WixQuietExec stdout/stderr) |
| `%TEMP%\bad-msi-cleanup.log` | uninstall CA |

Коды `write-config`: `BAD_MSI_000` OK; `001` нет `bad-paths.ps1`; `002` ProgramData; `003` config.json; `004` ACL; `005` прочее.

Явный verbose (если нужен отдельный файл):

```powershell
msiexec /i bad-agent-0.10.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn /l*v "$env:TEMP\bad-agent-install.log"
```

Не шарьте `/l*v` с `ENROLLMENTTOKEN` — см. SEC-011 выше.

### Uninstall

```powershell
msiexec /x bad-agent-0.10.1.msi /qn
```

При полном uninstall (не upgrade): служба Stop+Remove, файлы Program Files снимаются, `cleanup-uninstall.ps1` удаляет `config.json`, `queue\`, `logs\` (enrollment leftovers). Запись PATH от `ADDPATH=1` снимается.

## Вырезать релиз

```bash
git tag v0.10.1
git push origin v0.10.1
# → workflow release-msi публикует MSI (+ Authenticode, если secrets) + agent-release.json
# → on-prem сервер sync'ит с GitHub Release (admin sync или фоновый job)
# → агенты опрашивают GET /v1/agent/update/check и ставят через msiexec
```

## UpgradeCode

Стабильный `UpgradeCode` MSI: `BADA0001-BADA-4B01-8BAD-00BADA000001` (валидный GUID; прежний суффикс `BLAZERITY0BAD` WiX 5 отклонял как не-hex). Component Guid: `…000003`…`…000006`.

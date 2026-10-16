# bAD Agent MSI (WiX)

Сборка только на Windows. Исходники в репозитории; **Linux CI MSI-бинарник не выпускает**.

Workflow GitHub Actions [`.github/workflows/release-msi.yml`](../../.github/workflows/release-msi.yml) собирает на `windows-latest` по тегу **`agent-v*`** (переходно голый `v*` = agent) или `workflow_dispatch` и загружает:

- `bad-agent-<agent-semver>.msi`
- `agent-release.json` (`version`, `msi_name`, `sha256`)

в GitHub Release для тега агента. Semver MSI = **только agent** (`agent/VERSION` / csproj); корневой/`server` `VERSION` панели **не** читается. `server-v*` MSI не триггерит.

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
  /f .\codesign.pfx /p <password> .\bad-agent-<версия из agent/VERSION>.msi
```

Semver для команд ниже — из [`agent/VERSION`](../../agent/VERSION) (не корневой `VERSION`).

## Локальная сборка (Windows)

```powershell
# 1. Установить WiX v5 как .NET tool (один раз)
dotnet tool install --global wix --version 5.0.2
# --global: иначе extension в cwd-local .wix и `wix build -ext …` даёт WIX0144
wix extension add --global WixToolset.Util.wixext/5.0.2

# 2. Publish агента ($ver = содержимое agent/VERSION)
$ver = (Get-Content ..\..\agent\VERSION -Raw).Trim()
dotnet publish ..\..\agent\src\BadAgent\BadAgent.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:Version=$ver `
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
  -d ProductVersion=$ver `
  -o "bad-agent-$ver.msi"
```

## Установка / апгрейд

```powershell
msiexec /i bad-agent-<версия из agent/VERSION>.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn
```

Опционально: добавить каталог установки в **Machine PATH**, чтобы команда `bad` работала из cmd.exe / Win+R (`bad.cmd` → `BadAgent.exe`). По умолчанию **выключено** (`ADDPATH=0` / не указано).

```powershell
msiexec /i bad-agent-<версия из agent/VERSION>.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  ADDPATH=1 `
  /qn
```

Public properties: `SERVERURL`, `ENROLLMENTTOKEN`, `ADDPATH` (опционально).

### Не ставить против HTTP bootstrap

Сервер 0.11 может кратко жить на **HTTP** только для панели (смена пароля → upload cert → HTTPS). Агенты в этот режим **не** входят:

- **Не** передавайте `SERVERURL=http://…` в MSI против bootstrap-сервера. Агент по умолчанию отклоняет cleartext; lab opt-in `BAD_ALLOW_HTTP=1` — только стенд, не бой.
- Ставьте MSI **после** HTTPS на nginx (`SERVERURL=https://…`). HTTP bootstrap панели ≠ поддержка HTTP-агента.

### Enrollment token и командная строка (SEC-011)

Deferred CA `write-config.ps1` **не** получает `ENROLLMENTTOKEN` / `SERVERURL` в argv PowerShell и **не** кладёт token в CustomActionData. WiX пишет их в `HKLM\SOFTWARE\blazerity\bAD\Setup` через `RegistryValue`; скрипт читает ключ, кладёт token в `config.json` (ACL: Administrators+SYSTEM) и **сразу удаляет** `Setup`. Этот контракт не менять.

**Остаточный риск (документируем):**

- Токен всё ещё может быть на **родительской** командной строке оператора: `msiexec /i … ENROLLMENTTOKEN=…` (видно в process list / истории shell на время install).
- При `msiexec /l*v` (и встроенном `MsiLogging=voicewarmupx` → `%TEMP%\MSI*.log`) verbose-лог может содержать значения public properties, включая enrollment token.
- Кратковременно token лежит в registry `Setup` до конца `write-config` (LocalSystem); при обрыве install ключ снимает `cleanup-uninstall.ps1` / компонент.

**Обязательно для операторов:**

1. **Не шарить** `/l*v` / `%TEMP%\MSI*.log` с `ENROLLMENTTOKEN` (чаты, wiki, тикеты, долгоживущие шары).
2. **После волны** массового деплоя MSI — **ротировать** site enrollment token (Параметры → Обновления агента / runbook в [operator-guide.md](../../docs/operator-guide.md)).
3. Доставлять команду install через защищённый канал (Intune/GPO secret), не chat/wiki.

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

Явный verbose (если нужен отдельный файл для отладки **локально**):

```powershell
msiexec /i bad-agent-<версия из agent/VERSION>.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=your-enrollment-token `
  /qn /l*v "$env:TEMP\bad-agent-install.log"
```

**Не шарить** этот лог (и `%TEMP%\MSI*.log`): в нём может быть `ENROLLMENTTOKEN`. После волны установки — ротация enrollment token (см. SEC-011 выше).

### Uninstall

```powershell
msiexec /x bad-agent-<версия из agent/VERSION>.msi /qn
```

При полном uninstall (не upgrade): служба Stop+Remove, файлы Program Files снимаются, `cleanup-uninstall.ps1` удаляет `config.json`, `queue\`, `logs\` (enrollment leftovers). Запись PATH от `ADDPATH=1` снимается.

## Вырезать релиз (agent line)

```bash
# bump agent/VERSION (+ csproj через Directory.Build.props) — не корневой VERSION сервера
VER=$(tr -d '[:space:]' < agent/VERSION)
git tag "agent-v${VER}"
git push origin "agent-v${VER}"
# → release-msi: ProductVersion = agent semver → MSI + agent-release.json на Release agent-v<VER>
# → on-prem sync / ingest зеркала агента
# Переходный alias: голый v* ещё = agent; server bumps — только server-v* (без MSI).
```

Semver в CI: `inputs.version` → tag `agent-v*`/`v*` → `agent/VERSION` → else csproj. **Запрет:** читать корневой или server `VERSION`.

## Сборка из панели (опционально)

Отдельный путь волны «Обновление сервера»: кнопка в UI **не** собирает MSI локально и **не** трогает self-update панели (`/var/lib/bad/server-releases/`). Только trigger GitHub Actions → артефакт → ingest в **зеркало агента** (`BAD_AGENT_UPDATES_DIR` / `ingest_uploaded_msi`). Authenticode для этого пути **не** требуется (unsigned OK). В `inputs.version` передавать **agent** semver, не server `VERSION`.

| Что | Значение |
|-----|----------|
| Workflow | `release-msi` (`.github/workflows/release-msi.yml`) |
| Trigger | `workflow_dispatch` (Actions UI или `POST …/actions/workflows/release-msi.yml/dispatches`) |
| `ref` | ветка исходников (часто `main`); version = agent semver отдельно |
| `inputs.version` | **agent** semver (предпочтительно для панели); пусто → `agent/VERSION` или csproj |
| `inputs.publish_release` | `true` (default) → GitHub Release `agent-v<semver>`; `false` → только Actions artifact |
| Artifact | имя `bad-agent-msi-<agent-semver>`; внутри `bad-agent-<ver>.msi` + `agent-release.json` |
| Job outputs | `version`, `msi_name`, `artifact_name`, `tag` после success |
| Ingest | Release path → `sync_from_github`; artifact path → `ingest_uploaded_msi` (+ manifest) |
| Token (`BAD_GITHUB_TOKEN`) | `actions:write` (dispatch); артефакт — `actions:read`; Release — `contents:read` |

Ошибки GH/quota / failed run — зона Server Lead (RU-сообщения в UI); MSI workflow при fail просто не отдаёт артефакт. Не смешивать кнопку sync MSI и Apply server update.

## UpgradeCode

Стабильный `UpgradeCode` MSI: `BADA0001-BADA-4B01-8BAD-00BADA000001` (валидный GUID; прежний суффикс `BLAZERITY0BAD` WiX 5 отклонял как не-hex). Component Guid: `…000003`…`…000006`.

# Заметки для coding agents (bAD)

Практическая карта репозитория: где что лежит, как гонять тесты, что нельзя сломать. Версия продукта: **1.0.0**.

## Структура

```
agent/                 # .NET 8 Worker + service CLI
  src/BadAgent/        # код службы (Worker, AgentUpdater, ServiceCli, …)
server/                # FastAPI app + agent-update mirror
  bad_server/          # пакет приложения
installer/msi/         # WiX Product.wxs, write-config.ps1, bad.cmd
deploy/debian/         # install.sh, systemd/, nginx/
docs/                  # операторские и архитектурные документы
VERSION                # канонический semver продукта (сейчас 1.0.0)
.github/workflows/     # ci.yml + release-msi.yml
```

Unit tests — **только локально** (gitignored, не в GitHub): `agent/tests/`, `server/tests/`. CI их не запускает.

## Как запустить сервер (dev)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DB_PATH=./data/bad.db
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes
# optional: disable GitHub sync noise in local/dev
export BAD_AGENT_UPDATE_SYNC_ON_STARTUP=false
export BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS=0

uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
# локально, если есть untracked server/tests/: pytest -q
```

- Health: `GET /v1/health` → `{"status":"ok","version":"1.0.0"}`
- Web: `/login` (`admin`/`admin` first boot) → `/` обзор; устройства `/devices` (поиск/CSV/архив); карточка — revoke/rotate/delete
- Параметры `/settings/*` (Win11 left-nav): LDAP (+ AD group), mail/SMTP toggles, retention, backups, policies, agent updates
- UI look: Win11/Fluent light + русский UI — `bad_server/static/style.css`, favicon; CLI HTML report — те же токены/иконки; `agent/assets/bad.ico`

## Как собрать / тестировать агент

```bash
cd agent
dotnet build BadAgent.sln -c Release
# локально, если есть untracked agent/tests/:
#   dotnet test tests/BadAgent.Tests -c Release
```

Локальный прогон против сервера — **только `https://`** в `BAD_SERVER_URL` / `server_url`:

```bash
export BAD_CONFIG_DIR=/tmp/bad-agent-config
export BAD_SERVER_URL=https://bad.example.com
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
dotnet run --project src/BadAgent -c Release
```

Lab/cleartext (uvicorn без TLS): `BAD_SERVER_URL=http://127.0.0.1:8000` **и** `BAD_ALLOW_HTTP=1` — не для production и не копировать в MSI/`SERVERURL`.

На Windows в проде — только MSI + HTTPS.

## Локальный CLI (`bad`) и Service CLI

Тот же `BadAgent.exe` (shim `bad.cmd` рядом в MSI). Режим:

1. `service …` — управление службой (elevated).
2. Интерактивный запуск (консоль / Win+R) — локальные отчёты inventory (**без** обращения к серверу).
3. Запуск SCM — Windows Service host (без изменений).

```powershell
bad                     # ASCII-отчёт (то же: bad report | bad info)
bad -r [path]           # HTML-отчёт (--report; устар. --html)
bad -c                  # интерактивная настройка (рекомендуется)
bad -h                  # справка (--help | -?)
bad config              # показать настройки (без api_key / enrollment_token)
bad config set <k> <v>  # power-user: один knob
BadAgent.exe service status|start|stop|restart
```

> Основной путь настройки: **`bad -c`** (пустой ввод = оставить текущее). `-h` — только справка; HTML: `-r`.

Учитываются `collect_*` из `%ProgramData%\blazerity\bAD\config.json`. Код: `BadCli`, `ConfigCli`, `AsciiReportWriter`, `HtmlReportWriter`, `ReportPathResolver`.

`bad -c` / `config set` пишут allowlisted knobs и ставят `agent_local_keys` / `server_url_local` → heartbeat `config_local` (панель: **«задано на агенте»**). Значения `api_key` / `enrollment_token` CLI **не** печатает и не задаёт.

Локальные отчёты **не** ходят на сервер и **не** предлагают `http://` как `server_url`. Служба при cleartext без opt-in падает с русской подсказкой (`BadApiClient.CleartextHttpRejectedMessage`: нужен `https://`, `BAD_ALLOW_HTTP=1` только lab).

Порядок разделов отчёта (Speccy / карточка устройства): **ОС → Процессор → Материнская плата → Память → Видео → Накопители → Мониторы → Батарея → Сеть → Пользователи → ПО → …**.

Опционально MSI `ADDPATH=1` добавляет каталог установки в Machine PATH (по умолчанию PATH не трогаем).

Реализация service: `System.ServiceProcess.ServiceController`. На Linux команды управления возвращают ошибку (unit-тесты покрывают help/unknown/non-Windows).

## Self-update (агент ← сервер ← GitHub)

Агенты **не** ходят в GitHub.

1. GHA `release-msi` публикует MSI + `agent-release.json` в Release.
2. Сервер sync’ит в `/var/lib/bad/agent-updates/` (+ SQLite `agent_update`).
3. Агент: `GET /v1/agent/update/check?current=` → follow `target_version` / `update_available` → download MSI (same-origin, `?version=`) → sha256 → `msiexec /i … /qn` → exit; WiX MajorUpgrade (**AllowDowngrades**). Gate: не только `IsNewer` — pin ниже current тоже применяется.

Конфиг: `update_enabled` (default true), `update_check_interval_hours` (default 24), **`update_target`** (`latest` | semver pin; алиас `desired_agent_version`). Env: `BAD_UPDATE_ENABLED`, `BAD_UPDATE_CHECK_INTERVAL_HOURS`, `BAD_UPDATE_TARGET`.

Сценарии: **upgrade**, **downgrade** (pin↓ / latest→older mirror), **same** (no-op), **latest** (target = site latest). Anti-loop: `pending_update_*` cooldown 2h.

Ключевые файлы: `AgentUpdater.cs`, `VersionUtil.cs`, `UpdatePathUtil.cs`, `server/bad_server/agent_update.py`, `github_release.py`.

## Удалённый конфиг агента

Эффективные настройки (remote merge): **defaults &lt; matching policies (priority asc) &lt; per-device override**.  
UI provenance на ключ: **`default` \| `policy` \| `device_override` \| `agent_local`** (`agent_local` только из отчёта агента).

| Endpoint | Auth |
|----------|------|
| `GET /v1/agent/config` | agent API key (только своё устройство) |
| `POST /v1/heartbeat` (+ optional `config_version`, optional `config_local`) | agent API key; ответ может содержать `config` |
| `GET/POST/PUT/DELETE /v1/admin/policies*` | admin Bearer |
| `GET /v1/admin/devices/{id}/config` | admin Bearer → + `sources` / `agent_local_keys` |
| `PUT/DELETE /v1/admin/devices/{id}/config-override` | admin Bearer |

Safe knobs: интервалы + `update_enabled` + **`update_target`** (`latest`|semver) + toggles коллекторов `collect_hardware` / `collect_users` / `collect_software`. Код: `server/bad_server/agent_config.py`, `ConfigStore.ApplyRemoteSettings`, `InventoryCollector` + `CollectorOptions`.

**`config_local` (контракт):** агент в heartbeat шлёт `keys` (manual / agent_local safe knobs) + опционально `settings` и display-only `server_url`. Server кладёт в `meta.config_local`, отдаёт `sources` на admin/web. Не путать с server `device_override`. Полный schema: [architecture.md — config source](architecture.md#api-notes-config-source-provenance).

Hardware (при `collect_hardware`): помимо CPU/RAM/disks/volumes — `serial_number`, `model`, `manufacturer`, `bios_version`, `battery`, `monitors[]`, `gpus[]`, `ram_modules[]` (+ `memory_type` на модуль), `ram_memory_type` (системный consensus). Host: `ad_ou` / `ad_distinguished_name` (domain-joined). Top-level `minidumps` — только метаданные BSOD (без upload тел). Low-impact: `ThreadPriority.BelowNormal` + yields между WMI. Soft-fail по подсекциям `hardware.*` / `host.ad_ou` / `minidumps`. Cap: 16 GPU / 32 DIMM / 8 monitors / 20 minidump files. Код: `InventoryCollector`, `HardwareMaps`, `OfflineQueue`, `WindowsEventLog`, модели в `InventoryModels.cs`.

Heartbeat health (опционально → meta устройства): `last_inventory_ok`, `last_inventory_error`, `agent_uptime_seconds`, `system_drive_free_bytes`. Рядом (отдельно): optional `config_local` → provenance.

### Web UI security

- **SEC-004:** при `must_change_password` UI пускает только `/account/password` и `/logout`; основная навигация скрыта.
- **SEC-010:** CSRF на всех HTML POST — `Depends(ensure_csrf)` (cookie `bad_csrf` + поле `csrf_token`); детали в [architecture.md](architecture.md).

### Offline queue / revoke

- Недоступный сервер → `%ProgramData%\blazerity\bAD\queue\` + backoff (`OfflineQueue`).
- 401/403 → очистить `api_key`, оставить `device_id`, Event Log, не постить до re-enroll/reinstall (`Worker.HandleAuthFailure`).
- Крупные сбои enroll/update/revoke → Application log, source `bAD Agent`.

### Security harden

- **SEC-002:** `msi_name` из update/check — только safe basename; путь обязан остаться в temp (`UpdatePathUtil.ResolveSafeMsiPath`).
- **SEC-009:** download MSI — только relative / same-origin к `server_url`; чужой absolute URL отвергается (`UpdatePathUtil.ResolveSameOriginUpdateUrl`).
- **SEC-011:** MSI write-config читает enrollment token из HKLM `…\Setup` (не argv PowerShell); residual risk родителя `msiexec … ENROLLMENTTOKEN=` — в `installer/msi/README.md`.

### MSI catalog / enrollment / site bundle

- Каталог `agent_msi_versions` + UI заливка MSI; GitHub sync сохраняется.
- Remote-config: `update_target` = `latest` | semver из зеркала (резолв на сервере в update/check).
- Enrollment rotate в Параметры → Обновления агента (hash в SQLite, без обязательного restart).
- Site bundle download + `deploy/debian/restore-site-bundle.sh`.
- Обзор: drift vs target, пустое зеркало, revoked active.

## Где живёт версия (bump checklist)

Канон: корневой файл **`VERSION`** (`1.0.0`). Bump: patch +0.0.1 / minor +0.1.0 / major только по решению владельца. При релизе синхронизировать:

| Место | Поле |
|-------|------|
| `VERSION` | одна строка semver |
| `server/bad_server/__init__.py` | `__version__` |
| `server/pyproject.toml` | `project.version` |
| `agent/src/BadAgent/BadAgent.csproj` | `Version`, `AssemblyVersion`, `FileVersion`, `InformationalVersion` |
| `agent/src/BadAgent/InventoryModels.cs` | default `AgentVersion` (fallback) |
| `agent/src/BadAgent/VersionUtil.cs` | fallback default |
| `installer/msi/Product.wxs` | `ProductVersion` / `Package/@Version` + имя `bad-agent-<semver>.msi` |
| `deploy/debian/install.sh` | default `BAD_VERSION` |
| тесты / README / operator-guide | ожидаемые строки версии при необходимости |

Агент отправляет `agent_version` из assembly version (трёхкомпонентный semver). Сервер отдаёт версию в `/v1/health` и в footer web UI.

`schema_version` inventory (**integer `1`|`2`**; агент 0.4+ шлёт `2` с optional `software`) — отдельный контракт; не менять вместе с semver без миграции протокола.

Релиз MSI: `git tag vX.Y.Z && git push origin vX.Y.Z` → см. [guideline.md](guideline.md).

## Инварианты — не ломать

1. **HTTPS-only** для агента в нормальном режиме; reject cleartext (`https://` в `server_url`; `BAD_ALLOW_HTTP=1` только lab).
2. **Три разных секрета**: enrollment ≠ API key ≠ admin.
3. **Hash в БД**, plaintext API key только в ProgramData с жёстким ACL.
4. **Upsert по `device_id`**; MSI upgrade сохраняет ProgramData (не требовать re-enroll).
5. **uvicorn localhost-only**; TLS на nginx.
6. **Web UI за session login**; `/devices` без сессии → redirect `/login`.
7. **OpenAPI UI выключен** в приложении.
8. Сбой одного collector не валит весь snapshot (`collector_errors`).
9. **Агент не ходит в GitHub** за обновлениями — только server mirror.
10. **Не логировать** enrollment/admin/API/GitHub tokens.

## MSI

- Источники: `installer/msi/Product.wxs`, `write-config.ps1`, `cleanup-uninstall.ps1`.
- Сборка **только на Windows** (локально или GHA `release-msi`): см. `installer/msi/README.md`.
- Public properties: `SERVERURL`, `ENROLLMENTTOKEN` → ProgramData; optional `ADDPATH=1` → Machine PATH + `bad.cmd`.
- UpgradeCode фиксирован; major upgrade, ProgramData не сносить (`Permanent`); полный uninstall — Stop/Remove службы + `cleanup-uninstall.ps1` (config/queue/logs).
- Authenticode: secrets `CODE_SIGN_PFX_BASE64` + `CODE_SIGN_PFX_PASSWORD` (optional timestamp URL); без них — unsigned MSI.
- Артефакт: `bad-agent-1.0.0.msi` + `agent-release.json` (сервер/Debian могут быть на другом semver — см. корневой `VERSION`).
- Сбой CA до Serilog: `logs\msi-install.log` + `BAD_MSI_###`; msiexec `%TEMP%\MSI*.log`.

## Debian install

- Скрипт: `deploy/debian/install.sh`.
- Требует root; рассчитан на Debian 12.
- Кладёт app в `/opt/bad`, БД `/var/lib/bad/bad.db`, updates `/var/lib/bad/agent-updates/`, env `/etc/bad/site.env`.
- Unit: `deploy/debian/systemd/bad-api.service` → `bad-api.service`.
- nginx template: `deploy/debian/nginx/bad.conf.template`.
- Печатает enrollment + admin tokens **один раз** при первом создании `site.env`.

## Полезные файлы

| Задача | Файл |
|--------|------|
| Маршруты API / гайд 1C | `server/bad_server/api.py`, [api-v1.md](api-v1.md) |
| Remote config / policies | `server/bad_server/agent_config.py` |
| Agent update mirror | `server/bad_server/agent_update.py`, `github_release.py` |
| Web routes | `server/bad_server/web.py` |
| Схема/settings | `server/bad_server/schemas.py`, `config.py` |
| DB | `server/bad_server/db.py` |
| Worker loop | `agent/src/BadAgent/Worker.cs` |
| Self-update | `agent/src/BadAgent/AgentUpdater.cs` |
| Service CLI | `agent/src/BadAgent/ServiceCli.cs` |
| Local CLI / reports | `BadCli.cs`, `AsciiReportWriter.cs`, `HtmlReportWriter.cs` |
| HTTP client | `agent/src/BadAgent/BadApiClient.cs` |
| Collectors | `agent/src/BadAgent/InventoryCollector.cs`, `HardwareMaps.cs` |
| MSI PATH shim | `installer/msi/bad.cmd`, `ADDPATH` in `Product.wxs` |
| Release MSI | `.github/workflows/release-msi.yml` |
| Оператор | `docs/operator-guide.md` |

## CI

- `.github/workflows/ci.yml`: import-check + ruff в `server/`, `dotnet build` Release в `agent/` (Linux; **без** pytest/dotnet test и **без** MSI). Тесты — local-only.
- `.github/workflows/release-msi.yml`: Windows, тег `v*` / dispatch → GitHub Release.

## Карта auth (не перепутать)

| Механизм | Где | Назначение |
|----------|-----|------------|
| Enrollment Bearer | `POST /v1/enroll` | одноразовый обмен на API key агента |
| Agent API key | heartbeat / inventory / `GET /v1/agent/config` | per-device |
| Admin Bearer | `GET /v1/devices*`, policies, overrides, `POST /v1/admin/enrollment/rotate` | автоматизация / curl |
| Local user session | web cookie `bad_session` | операторы в браузере |
| LDAP (опционально) | fallback входа в web | пользователи каталога → session |

**Transport (API notes):** в prod enroll и agent API — **HTTPS**. Cleartext только lab (`BAD_ALLOW_HTTP=1` на агенте). При managed TLS cleartext `/v1/enroll` → **403** (`HTTPS required for enrollment…`; lab: `BAD_ALLOW_ENROLL_OVER_HTTP=1`). `POST /v1/admin/enrollment/rotate` — не вызывать и не логировать plaintext `token` по незащищённым каналам. Полный контракт: [architecture.md — API notes](architecture.md#api-notes-transport-https-и-enrollment).

Код: `server/bad_server/auth.py`, `sessions.py`, `ldap_client.py`, `web.py`, `crypto_util.py`.

Seed локального admin только если `COUNT(local_users)=0`.

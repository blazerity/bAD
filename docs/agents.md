# Заметки для coding agents (bAD)

Практическая карта репозитория: где что лежит, как гонять тесты, что нельзя сломать.

**Две линии semver:** сервер (`VERSION`) и агент (`agent/VERSION`). Не путать panel **Обновление сервера** и MSI / **Обновления агента**.

## Структура

```
agent/                 # .NET 8 Worker + service CLI
  VERSION              # канон semver агента (MSI / assembly)
  src/BadAgent/        # код службы (Worker, AgentUpdater, ServiceCli, …)
server/                # FastAPI app + agent-update mirror
  bad_server/          # пакет приложения
installer/msi/         # WiX Product.wxs, write-config.ps1, bad.cmd
deploy/debian/         # install.sh, systemd/, nginx/
docs/                  # операторские и архитектурные документы
VERSION                # канон semver сервера (health / footer / panel-update)
.github/workflows/     # ci.yml + release-msi.yml
```

Unit tests — **только локально** (gitignored, не в GitHub): `agent/tests/`, `server/tests/`. CI их не запускает.

## Как запустить сервер (dev)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DATABASE_URL=postgresql://bad:bad@127.0.0.1:5432/bad
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes
# optional: disable GitHub sync noise in local/dev
export BAD_AGENT_UPDATE_SYNC_ON_STARTUP=false
export BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS=0

uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
# локально, если есть untracked server/tests/: pytest -q
```

- Health: `GET /v1/health` → `{"status":"ok","version":"<server VERSION>"}`
- Web: `/login` (`admin`/`admin` first boot) → `/` обзор; устройства `/devices` (поиск/CSV/архив); карточка — revoke/rotate/delete
- Параметры `/settings/*` (Win11 left-nav): LDAP (+ AD group), mail/SMTP (notify toggles, `digest_interval_hours`; все включённые типы — одна periodic digest), retention, backups, policies, agent updates
- UI look: Win11/Fluent light + русский UI — `bad_server/static/style.css`, favicon; CLI HTML report — те же токены/иконки; `agent/assets/bad.ico`

## Обзор, поиск, события

Обзор `/` и Дашборд `/dashboard` используют одну сводку по парку (`web._fleet_snapshot` → `db.list_fleet_active_archived`): active/archived, stats и ops-блок без повторного полного обхода устройств. Сигналы «отстают от целевой версии» считаются по `meta` и batch override, без `get_device_detail` на каждую строку. `POST /v1/inventory` кэширует в `devices.meta` поля `domain`, `os`, `hardware_manufacturer`, `hardware_model`, `serial_number`, `chassis_type` (`device_meta.py`) — списки и дашборд читают meta, не полный snapshot.

Live-поиск: `static/panel-search.js` (debounce) → `GET /devices/search.json?q=` (сессия web, не admin Bearer; до 50). Важность события — по типу в `event_importance.py` (не колонка БД). UI `/events` и `GET /v1/events` принимают `q` (summary / type / hostname / device_id) и `importance`: `medium`|`high`|`critical` = не ниже порога, `all` = все, пусто = medium и выше (low скрыт).

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

Shim `bad.cmd` → `bin\BadAgent.exe` в `%ProgramFiles%\blazerity\bad agent\`. Режим:

1. `service …` — управление службой (elevated).
2. Интерактивный запуск (консоль / Win+R) — локальные отчёты inventory (**без** обращения к серверу).
3. Запуск SCM — Windows Service host (без изменений).

```powershell
bad                     # ASCII-отчёт inventory — любой пользователь
bad -r [path]           # HTML-отчёт
bad -h                  # справка
bad -c                  # интерактивная настройка — только elevated (администратор)
bad config set <k> <v>  # один knob — только elevated
bad config unset <k>    # сброс knob — только elevated
bad push                # синхронизация: очередь → inventory → heartbeat (config с сервера)
bad update              # проверка и установка MSI с сервера
bad service status|start|stop|restart   # служба badagent — elevated
```

MSI **2.0+:** `%ProgramFiles%\blazerity\bad agent\`; служба **`badagent`**. Апгрейд с 1.x: MajorUpgrade + `migrate-legacy-install.ps1` (см. `installer/msi/README.md`).

> Обычный пользователь: **`bad`**, **`bad -r`**, **`-h`**. Настройка: **`bad -c`** / **`config set|unset`** — запуск от администратора.

Учитываются `collect_*` из `%ProgramData%\blazerity\bAD\config.json` (если файл доступен на чтение; иначе — значения по умолчанию). Локальные отчёты **не** создают каталог `logs` в ProgramData. Код: `BadCli`, `ConfigStore.LoadForReport`, `ConfigCli`, `AsciiReportWriter`, `HtmlReportWriter`, `ReportPathResolver`.

`bad -c` / `bad config set|unset` пишут allowlisted knobs и ставят `agent_local_keys` / `server_url_local` → heartbeat `config_local` (панель: **«задано на агенте»**). Значения `api_key` / `enrollment_token` CLI **не** печатает и не задаёт.

В web UI и HTML-отчёте (`bad -r`) время показывается **относительно** («N мин. назад» и т.п., `local-time.js` / `TimeFormat.FormatFreshness*`); точное локальное — в подсказке (**ЧЧ:ММ:СС ДД.ММ.ГГГГ**). В JSON/API и БД — только UTC ISO.

Локальные отчёты **не** ходят на сервер и **не** предлагают `http://` как `server_url`. Служба при cleartext без opt-in падает с русской подсказкой (`BadApiClient.CleartextHttpRejectedMessage`: нужен `https://`, `BAD_ALLOW_HTTP=1` только lab).

Порядок разделов отчёта (Speccy / карточка устройства): **ОС → Процессор → Материнская плата → Память → Видео → Накопители → Мониторы → Батарея → Сеть → Пользователи → ПО → …**.

MSI по умолчанию добавляет каталог установки в Machine PATH (`ADDPATH=1`); отключить: `ADDPATH=0`.

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
| `POST /v1/heartbeat` (+ optional `config_version`, optional `config_local`) | agent API key; ответ может содержать `config`; при панельном refresh — всегда `config` + optional `actions` (`inventory`, `update_check`) |
| `POST /v1/devices/{id}/request-refresh` | admin Bearer → meta `refresh_*` для следующего heartbeat |
| `GET/POST/PUT/DELETE /v1/admin/policies*` | admin Bearer |
| `GET /v1/admin/devices/{id}/config` | admin Bearer → + `sources` / `agent_local_keys` |
| `PUT/DELETE /v1/admin/devices/{id}/config-override` | admin Bearer |

Safe knobs: интервалы + `update_enabled` + **`update_target`** (`latest`|semver) + toggles коллекторов `collect_hardware` / `collect_users` / `collect_software`. Код: `server/bad_server/agent_config.py`, `ConfigStore.ApplyRemoteSettings`, `InventoryCollector` + `CollectorOptions`.

**`config_local` (контракт):** агент в heartbeat шлёт `keys` (manual / agent_local safe knobs) + опционально `settings` и display-only `server_url`. Server кладёт в `meta.config_local`, отдаёт `sources` на admin/web. Не путать с server `device_override`. Полный schema: [architecture.md — config source](architecture.md#api-notes-config-source-provenance).

Hardware (при `collect_hardware`): помимо CPU/RAM/disks/volumes — `serial_number`, `model`, `manufacturer`, `chassis_type`, `bios_version`, `battery`, `monitors[]`, `gpus[]`, `ram_modules[]` (+ `memory_type` на модуль), `ram_memory_type` (системный consensus). Секция корпуса (`hardware.chassis`) — **всегда**, независимо от `collect_hardware`. Host: `ad_ou` / `ad_distinguished_name` (domain-joined). Top-level `minidumps` — только метаданные BSOD (без upload тел). In-process кэш тяжёлых секций (`HeavySectionCache` в `InventoryCollector`: software, minidumps, ram_modules при неизменном fingerprint). Low-impact: `ThreadPriority.BelowNormal` + yields между WMI. Soft-fail по подсекциям `hardware.*` / `host.ad_ou` / `minidumps`. Cap: 16 GPU / 32 DIMM / 8 monitors / 20 minidump files. Код: `InventoryCollector`, `HardwareMaps`, `OfflineQueue`, `WindowsEventLog`, модели в `InventoryModels.cs`.

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
- Смена enrollment-токена: Параметры → Обновления агента (хэш в Postgres, restart API не нужен); после смены UI показывает токен и готовую команду `msiexec` (`ADDPATH=1` по умолчанию) с кнопкой копирования.
- Site bundle download + `deploy/debian/restore-site-bundle.sh`.
- Обзор: drift vs target, пустое зеркало, revoked active.

## Где живёт версия (bump checklist)

Две линии semver: **server** = корневой `VERSION`; **agent** = `agent/VERSION`. Major — только владелец. Не бампать MSI/agent при server-only релизе.

### Server

| Место | Поле |
|-------|------|
| `VERSION` (корень) | одна строка semver |
| `server/bad_server/__init__.py` | `__version__` |
| `server/pyproject.toml` | `project.version` |
| `deploy/debian/install.sh` | default `BAD_VERSION` |

Tag: **`server-vX.Y.Z`**. Не триггерит MSI. Panel **Обновление сервера** — только server line.

### Agent

| Место | Поле |
|-------|------|
| **`agent/VERSION`** | канон agent semver (`1.0.x`); **не** читать корневой `VERSION` |
| `agent/Directory.Build.props` | `Version` / Assembly* / Informational ← `agent/VERSION` |
| `agent/src/BadAgent/InventoryModels.cs` | default `AgentVersion` (fallback = agent/VERSION) |
| `agent/src/BadAgent/VersionUtil.cs` | fallback default (= agent/VERSION) |
| `installer/msi/Product.wxs` | `ProductVersion` из того же semver, что publish/MSI |
| `release-msi` | input `version` → tag `agent-v*`/`v*` → **`agent/VERSION`** |

Агент отправляет `agent_version` из assembly (трёхкомпонентный semver). Сервер в `/v1/health` / footer — **server** VERSION.

`schema_version` inventory (**integer `1`|`2`**; агент 0.4+ шлёт `2` с optional `software`) — отдельный контракт; не менять вместе с semver без миграции протокола.

Релиз MSI: tag **`agent-vX.Y.Z`** (переходно `v*`) → см. [guideline.md](guideline.md).

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
- Public properties: `SERVERURL`, `ENROLLMENTTOKEN` → ProgramData; `ADDPATH` default `1` → Machine PATH + `bad.cmd` (`ADDPATH=0` — не менять PATH).
- UpgradeCode фиксирован; major upgrade, ProgramData не сносить (`Permanent`); полный uninstall — Stop/Remove службы + `cleanup-uninstall.ps1` (config/queue/logs).
- Authenticode: secrets `CODE_SIGN_PFX_BASE64` + `CODE_SIGN_PFX_PASSWORD` (optional timestamp URL); без них — unsigned MSI.
- Артефакт: `bad-agent-<agent-semver>.msi` + `agent-release.json`. Server (`VERSION`) — другая линия; не синхронизировать с MSI без правок агента.
- Сбой CA до Serilog: `logs\msi-install.log` + `BAD_MSI_###`; msiexec `%TEMP%\MSI*.log`.

## Debian install

- Скрипт: `deploy/debian/install.sh`.
- Требует root; рассчитан на Debian 12.
- Кладёт app в `/opt/bad`, Postgres (URL в `site.env`), зеркало MSI `/var/lib/bad/agent-updates/`, env `/etc/bad/site.env`.
- Unit: `deploy/debian/systemd/bad-api.service` → `bad-api.service`.
- nginx template: `deploy/debian/nginx/bad.conf.template`.
- Печатает enrollment + admin tokens **один раз** при первом создании `site.env`.

## Полезные файлы

| Задача | Файл |
|--------|------|
| Маршруты API / гайд 1C | `server/bad_server/api.py`, [api-v1.md](api-v1.md) |
| Remote config / policies | `server/bad_server/agent_config.py` |
| Agent update mirror | `server/bad_server/agent_update.py`, `github_release.py` |
| Web routes / мастер | `server/bad_server/web.py` (`GET /setup/progress.json`, каталог устройств, карточка) |
| Кэш meta + тип корпуса | `server/bad_server/device_meta.py` |
| Cleartext enroll guard | `server/bad_server/http_bootstrap.py`, вызов в `api.py` |
| Иконки корпуса / ссылки | `templates/macros/ui.html`, `macros/icons.html` |
| Относительное время UI | `static/local-time.js` |
| Схема/settings | `server/bad_server/schemas.py`, `config.py` |
| DB / лента событий (slim API) | `server/bad_server/db.py` (`list_device_events`, `include_detail`) |
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
- `.github/workflows/release-msi.yml`: Windows, тег `agent-v*` (переходно `v*`) / `workflow_dispatch` с agent `version` → GitHub Release.

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

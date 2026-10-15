# Заметки для coding agents (bAD)

Практическая карта репозитория: где что лежит, как гонять тесты, что нельзя сломать. Версия продукта: **0.8.0**.

## Layout

```
agent/                 # .NET 8 Worker + service CLI
  src/BadAgent/        # код службы (Worker, AgentUpdater, ServiceCli, …)
server/                # FastAPI app + agent-update mirror
  bad_server/          # пакет приложения
installer/msi/         # WiX Product.wxs, write-config.ps1, bad.cmd
deploy/debian/         # install.sh, systemd/, nginx/
docs/                  # операторские и архитектурные документы
VERSION                # канонический semver продукта (сейчас 0.8.0)
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

- Health: `GET /v1/health` → `{"status":"ok","version":"0.8.0"}`
- Web: `/login` (`admin`/`admin` first boot) → `/` обзор; устройства `/devices` (поиск/CSV/архив); карточка — revoke/rotate/delete
- Параметры `/settings/*` (Win11 left-nav): LDAP (+ AD group), mail/SMTP toggles, retention, backups, policies, agent updates
- UI look (0.8.0): Win11/Fluent light + русский UI — `bad_server/static/style.css`, favicon; CLI HTML report — те же токены/иконки; `agent/assets/bad.ico`

## Как собрать / тестировать агент

```bash
cd agent
dotnet build BadAgent.sln -c Release
# локально, если есть untracked agent/tests/:
#   dotnet test tests/BadAgent.Tests -c Release
```

Локальный прогон против HTTP-сервера:

```bash
export BAD_CONFIG_DIR=/tmp/bad-agent-config
export BAD_SERVER_URL=http://127.0.0.1:8000
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ALLOW_HTTP=1
dotnet run --project src/BadAgent -c Release
```

На Windows в проде — только MSI + HTTPS.

## Local CLI (`bad`) и Service CLI

Тот же `BadAgent.exe` (shim `bad.cmd` рядом в MSI). Режим:

1. `service …` — управление службой (elevated).
2. Интерактивный запуск (консоль / Win+R) — локальные отчёты inventory (**без** обращения к серверу).
3. Запуск SCM — Windows Service host (без изменений).

```powershell
bad                     # ASCII-отчёт (то же: bad report | bad info)
bad -h [path]           # HTML на Desktop или в path (то же: --html)
bad -?                  # справка (--help)
BadAgent.exe service status|start|stop|restart
```

Учитываются `collect_*` из `%ProgramData%\blazerity\bAD\config.json`. Код: `BadCli`, `AsciiReportWriter`, `HtmlReportWriter`, `ReportPathResolver`.

Опционально MSI `ADDPATH=1` добавляет каталог установки в Machine PATH (по умолчанию PATH не трогаем).

Реализация service: `System.ServiceProcess.ServiceController`. На Linux команды управления возвращают ошибку (unit-тесты покрывают help/unknown/non-Windows).

## Self-update (агент ← сервер ← GitHub)

Агенты **не** ходят в GitHub.

1. GHA `release-msi` публикует MSI + `agent-release.json` в Release.
2. Сервер sync’ит в `/var/lib/bad/agent-updates/` (+ SQLite `agent_update`).
3. Агент: `GET /v1/agent/update/check?current=` → download MSI → sha256 → `msiexec /i … /qn` → exit; WiX останавливает/стартует службу.

Конфиг: `update_enabled` (default true), `update_check_interval_hours` (default 24). Env: `BAD_UPDATE_ENABLED`, `BAD_UPDATE_CHECK_INTERVAL_HOURS`.

Ключевые файлы: `AgentUpdater.cs`, `VersionUtil.cs`, `server/bad_server/agent_update.py`, `github_release.py`.

## Remote agent config

Effective settings: **defaults &lt; matching policies (priority asc) &lt; per-device override**.

| Endpoint | Auth |
|----------|------|
| `GET /v1/agent/config` | agent API key (только своё устройство) |
| `POST /v1/heartbeat` (+ optional `config_version`) | agent API key; ответ может содержать `config` |
| `GET/POST/PUT/DELETE /v1/admin/policies*` | admin Bearer |
| `GET /v1/admin/devices/{id}/config` | admin Bearer |
| `PUT/DELETE /v1/admin/devices/{id}/config-override` | admin Bearer |

Safe knobs: intervals + `update_enabled` + collector toggles `collect_hardware` / `collect_users` / `collect_software`. Код: `server/bad_server/agent_config.py`, `ConfigStore.ApplyRemoteSettings`, `InventoryCollector` + `CollectorOptions`.

Hardware (при `collect_hardware`): помимо CPU/RAM/disks/volumes — `serial_number`, `model`, `manufacturer`, `gpus[]`, `ram_modules[]` (+ per-stick `memory_type`), `ram_memory_type` (system consensus). Тип памяти: map WMI `SMBIOSMemoryType` / `MemoryType` → `DDR4`/`DDR5`/`LPDDR4`/`LPDDR5`/… (`HardwareMaps.ResolveMemoryType`). Soft-fail по подсекциям `hardware.*`. Cap: 16 GPU / 32 DIMM. Код: `InventoryCollector`, `HardwareMaps`, модели в `InventoryModels.cs`.

Heartbeat health (optional → device meta): `last_inventory_ok`, `last_inventory_error`, `agent_uptime_seconds`, `system_drive_free_bytes`.

## Где живёт версия (bump checklist)

Канон: корневой файл **`VERSION`** (`0.8.0`). Bump: patch +0.0.1 / minor +0.1.0 / major только по решению владельца. При релизе синхронизировать:

| Место | Поле |
|-------|------|
| `VERSION` | одна строка semver |
| `server/bad_server/__init__.py` | `__version__` |
| `server/pyproject.toml` | `project.version` |
| `agent/src/BadAgent/BadAgent.csproj` | `Version`, `AssemblyVersion`, `FileVersion`, `InformationalVersion` |
| `agent/src/BadAgent/InventoryModels.cs` | default `AgentVersion` (fallback) |
| `agent/src/BadAgent/Worker.cs` | fallback string рядом с `Assembly.GetName().Version` |
| `installer/msi/Product.wxs` | `ProductVersion` / `Package/@Version` + имя `bad-agent-<semver>.msi` |
| `deploy/debian/install.sh` | default `BAD_VERSION` |
| тесты / README / operator-guide | ожидаемые строки версии при необходимости |

Агент отправляет `agent_version` из assembly version (трёхкомпонентный semver). Сервер отдаёт версию в `/v1/health` и в footer web UI.

`schema_version` inventory (**integer `1`|`2`**; агент 0.4+ шлёт `2` с optional `software`) — отдельный контракт; не менять вместе с semver без миграции протокола.

Релиз MSI: `git tag vX.Y.Z && git push origin vX.Y.Z` → см. [guideline.md](guideline.md).

## Инварианты — не ломать

1. **HTTPS-only** для агента в нормальном режиме; reject cleartext.
2. **Три разных секрета**: enrollment ≠ API key ≠ admin.
3. **Hash в БД**, plaintext API key только в ProgramData с жёстким ACL.
4. **Upsert по `device_id`**; MSI upgrade сохраняет ProgramData (не требовать re-enroll).
5. **uvicorn localhost-only**; TLS на nginx.
6. **Web UI read-only**; admin cookie/Bearer, без публичного доступа к `/devices`.
7. **OpenAPI UI выключен** в приложении.
8. Сбой одного collector не валит весь snapshot (`collector_errors`).
9. **Агент не ходит в GitHub** за обновлениями — только server mirror.
10. **Не логировать** enrollment/admin/API/GitHub tokens.

## MSI

- Источники: `installer/msi/Product.wxs`, `write-config.ps1`.
- Сборка **только на Windows** (локально или GHA `release-msi`): см. `installer/msi/README.md`.
- Public properties: `SERVERURL`, `ENROLLMENTTOKEN` → ProgramData; optional `ADDPATH=1` → Machine PATH + `bad.cmd`.
- UpgradeCode фиксирован; major upgrade, ProgramData не сносить (`Permanent`).
- Артефакт: `bad-agent-0.8.0.msi` + `agent-release.json`.

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
| Маршруты API | `server/bad_server/api.py` |
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

## Auth map (не перепутать)

| Механизм | Где | Назначение |
|----------|-----|------------|
| Enrollment Bearer | `POST /v1/enroll` | одноразовый обмен на API key агента |
| Agent API key | heartbeat / inventory / `GET /v1/agent/config` | per-device |
| Admin Bearer | `GET /v1/devices*`, policies, overrides | автоматизация / curl |
| Local user session | web cookie `bad_session` | операторы в браузере |
| LDAP (optional) | web login fallback | directory users → session |

Код: `server/bad_server/auth.py`, `sessions.py`, `ldap_client.py`, `web.py`, `crypto_util.py`.

Seed default admin только если `COUNT(local_users)=0`.

## Инварианты — не ломать

1. **HTTPS-only** для агента в нормальном режиме; reject cleartext.
2. **Три разных API-секрета**: enrollment ≠ API key ≠ admin token; плюс отдельные web-аккаунты.
3. **Hash в БД**, plaintext API key только в ProgramData с жёстким ACL.
4. **Upsert по `device_id`**; MSI upgrade сохраняет ProgramData (не требовать re-enroll).
5. **uvicorn localhost-only**; TLS на nginx.
6. **Web UI за session login**; `/devices` без сессии → redirect `/login`.
7. **OpenAPI UI выключен** в приложении.
8. Сбой одного collector не валит весь snapshot (`collector_errors`).
9. LDAP bind password не echo’ить в форме после save.

## MSI

- Источники: `installer/msi/Product.wxs`, `write-config.ps1`.
- Сборка **только на Windows** (WiX): см. `installer/msi/README.md`.
- Public properties: `SERVERURL`, `ENROLLMENTTOKEN`; optional `ADDPATH=1` for Machine PATH + `bad.cmd`.
- UpgradeCode фиксирован; major upgrade, ProgramData не сносить.
- Артефакт: `bad-agent-0.8.0.msi` (имя по semver).

## Debian install

- Скрипт: `deploy/debian/install.sh`.
- Требует root; рассчитан на Debian 12.
- Кладёт app в `/opt/bad`, БД `/var/lib/bad/bad.db`, env `/etc/bad/site.env`.
- Unit: `deploy/debian/systemd/bad-api.service` → `bad-api.service`.
- nginx template: `deploy/debian/nginx/bad.conf.template`.
- Печатает enrollment + admin API tokens **один раз** при первом создании `site.env`.
- Web: после первого старта — local `admin`/`admin` (сменить).

## Полезные файлы

| Задача | Файл |
|--------|------|
| Маршруты API | `server/bad_server/api.py` |
| Web routes / LDAP UI | `server/bad_server/web.py` |
| Auth helpers | `server/bad_server/auth.py` |
| LDAP client | `server/bad_server/ldap_client.py` |
| Sessions | `server/bad_server/sessions.py` |
| Схема/settings | `server/bad_server/schemas.py`, `config.py` |
| DB | `server/bad_server/db.py` |
| Worker loop | `agent/src/BadAgent/Worker.cs` |
| HTTP client | `agent/src/BadAgent/BadApiClient.cs` |
| Collectors | `agent/src/BadAgent/InventoryCollector.cs` |
| Оператор | `docs/operator-guide.md` |

## CI

`.github/workflows/ci.yml`: import-check + ruff (`server/`), `dotnet build` Release (`agent/`). Unit tests не в репо — гоняйте локально при наличии `*/tests/`.

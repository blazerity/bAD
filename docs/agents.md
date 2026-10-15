# Заметки для coding agents (bAD)

Практическая карта репозитория: где что лежит, как гонять тесты, что нельзя сломать.

## Layout

```
agent/                 # .NET 8 Worker + tests
  src/BadAgent/        # код службы
  tests/BadAgent.Tests/
server/                # FastAPI app
  bad_server/          # пакет приложения
  tests/               # pytest (не игнорировать в git — только кэши)
installer/msi/         # WiX Product.wxs, write-config.ps1
deploy/debian/         # install.sh, systemd/, nginx/
docs/                  # операторские и архитектурные документы
VERSION                # канонический semver продукта (сейчас 0.1.0)
```

Не путать: **не** игнорировать исходники `server/tests` и `agent/tests` — только `__pycache__`, `bin/`, `obj/`, coverage и т.п.

## Как запустить сервер (dev)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DB_PATH=./data/bad.db
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes

uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
pytest -q
```

- Health: `GET /v1/health` → `{"status":"ok","version":"0.1.0"}`
- Web: `/login` → `/devices`

## Как собрать / тестировать агент

```bash
cd agent
dotnet build BadAgent.sln -c Release
dotnet test BadAgent.sln -c Release
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

## Где живёт версия (bump checklist)

Канон: корневой файл **`VERSION`** (`0.1.0`). При релизе синхронизировать:

| Место | Поле |
|-------|------|
| `VERSION` | одна строка semver |
| `server/bad_server/__init__.py` | `__version__` |
| `server/pyproject.toml` | `project.version` |
| `agent/src/BadAgent/BadAgent.csproj` | `Version`, `AssemblyVersion`, `FileVersion`, `InformationalVersion` |
| `agent/src/BadAgent/InventoryModels.cs` | default `AgentVersion` (fallback) |
| `agent/src/BadAgent/Worker.cs` | fallback string рядом с `Assembly.GetName().Version` |
| `installer/msi/Product.wxs` | `Package/@Version` + имя `bad-agent-<semver>.msi` в комментарии |
| `deploy/debian/install.sh` | default `BAD_VERSION` |
| тесты / README / operator-guide | ожидаемые строки версии при необходимости |

Агент отправляет `agent_version` из assembly version (трёхкомпонентный semver). Сервер отдаёт версию в `/v1/health` и в footer web UI.

`schema_version` inventory (**integer `1`**) — отдельный контракт; не менять вместе с semver без миграции протокола.

## Инварианты — не ломать

1. **HTTPS-only** для агента в нормальном режиме; reject cleartext.
2. **Три разных секрета**: enrollment ≠ API key ≠ admin.
3. **Hash в БД**, plaintext API key только в ProgramData с жёстким ACL.
4. **Upsert по `device_id`**; MSI upgrade сохраняет ProgramData (не требовать re-enroll).
5. **uvicorn localhost-only**; TLS на nginx.
6. **Web UI read-only**; admin cookie/Bearer, без публичного доступа к `/devices`.
7. **OpenAPI UI выключен** в приложении.
8. Сбой одного collector не валит весь snapshot (`collector_errors`).

## MSI

- Источники: `installer/msi/Product.wxs`, `write-config.ps1`.
- Сборка **только на Windows** (WiX): см. `installer/msi/README.md`.
- Public properties: `SERVERURL`, `ENROLLMENTTOKEN` → пишутся в ProgramData custom action’ом.
- UpgradeCode фиксирован; major upgrade, ProgramData не сносить.
- Артефакт: `bad-agent-0.1.0.msi` (имя по semver).

## Debian install

- Скрипт: `deploy/debian/install.sh`.
- Требует root; рассчитан на Debian 12.
- Кладёт app в `/opt/bad`, БД `/var/lib/bad/bad.db`, env `/etc/bad/site.env`.
- Unit: `deploy/debian/systemd/bad-api.service` → `bad-api.service`.
- nginx template: `deploy/debian/nginx/bad.conf.template`.
- Печатает enrollment + admin tokens **один раз** при первом создании `site.env`.

## Полезные файлы

| Задача | Файл |
|--------|------|
| Маршруты API | `server/bad_server/api.py` |
| Web routes | `server/bad_server/web.py` |
| Схема/settings | `server/bad_server/schemas.py`, `config.py` |
| DB | `server/bad_server/db.py` |
| Worker loop | `agent/src/BadAgent/Worker.cs` |
| HTTP client | `agent/src/BadAgent/BadApiClient.cs` |
| Collectors | `agent/src/BadAgent/InventoryCollector.cs` |
| План (locked) | `docs/architecture-plan.md` |
| Оператор | `docs/operator-guide.md` |

## CI

`.github/workflows/ci.yml`: pytest в `server/`, `dotnet build/test` в `agent/`. Локально повторяйте те же команды перед PR.

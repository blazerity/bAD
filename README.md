# bAD — blazerity Asset Discovery

Лёгкий Windows-агент инвентаризации + on-prem сервер накопления снимков.

| Компонент | Стек |
|-----------|------|
| Агент | .NET 8 Worker Service (служба Windows), WiX MSI |
| Сервер | Python 3.11+ FastAPI + SQLite, uvicorn за nginx TLS |
| Deploy | `deploy/debian/install.sh` — установка одной командой на Debian 12 |

## Структура репозитория

```
agent/            # C# Worker Service + service CLI
server/           # FastAPI app, web UI, зеркало обновлений агента
installer/msi/    # исходники WiX (MSI собирается на Windows / GHA release-msi)
deploy/debian/    # install.sh, systemd, шаблон nginx
docs/             # архитектура, гайдлайны, заметки по агенту, операторский гайд
VERSION           # semver продукта (0.12.0)
.github/workflows # ci.yml (Linux build/import) + release-msi.yml (Windows, теги)
```

## Быстрый старт (сервер на Linux)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DB_PATH=./data/bad.db
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes

uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

- API health: http://127.0.0.1:8000/v1/health  
- Web UI: http://127.0.0.1:8000/login (по умолчанию `admin` / `admin` при первом запуске — смените)  
- Устройства: http://127.0.0.1:8000/devices  
- LDAP (admin): http://127.0.0.1:8000/settings/ldap  

Локальные тесты (если есть untracked дерево `server/tests/`):

```bash
pytest -q
```

## Агент (dev)

```bash
cd agent
dotnet build BadAgent.sln -c Release
# Локальные тесты (untracked agent/tests/): dotnet test tests/BadAgent.Tests -c Release

# server_url — https:// (prod). Cleartext http:// только lab + BAD_ALLOW_HTTP=1.
export BAD_CONFIG_DIR=/tmp/bad-agent-config
export BAD_SERVER_URL=https://bad.example.com
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
dotnet run --project src/BadAgent -c Release
```

На Windows установка службы через MSI (`installer/msi/`) с public properties `SERVERURL` (`https://…`) и `ENROLLMENTTOKEN`.

Локальный CLI (консоль): `bad` — ASCII; `bad -r` — HTML; `bad -c` — интерактивная настройка; `bad -h` — справка; `bad config` — просмотр (без секретов).

Управление службой (elevated):

```powershell
BadAgent.exe service status|start|stop|restart
```

Self-update: агенты опрашивают **сервер** (не GitHub) на наличие более нового зеркалированного MSI; см. [docs/architecture.md](docs/architecture.md).

## Релизы (агент MSI)

Тег `v0.10.0` (или ручной запуск `release-msi`) → Windows GHA собирает MSI + `agent-release.json` → GitHub Release → sync на сервере → апгрейд агентов. Linux CI MSI **не** собирает. Подробности: [docs/guideline.md](docs/guideline.md).

## Документация

| Документ | Описание |
|----------|----------|
| [docs/architecture.md](docs/architecture.md) | Архитектура + web LDAP auth + pipeline обновления агента |
| [docs/guideline.md](docs/guideline.md) | Инженерные правила + как релизить MSI |
| [docs/agents.md](docs/agents.md) | Агент, service CLI, version bump, LDAP/web auth map, инварианты |
| [docs/operator-guide.md](docs/operator-guide.md) | Операторский путь: Debian install → MSI → web UI |

## Путь оператора

См. [docs/operator-guide.md](docs/operator-guide.md): установка на Debian одной командой → MSI → устройство появляется в HTTPS web UI.

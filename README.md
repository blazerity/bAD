# bAD — blazerity Asset Discovery

Лёгкий Windows-агент инвентаризации и сервер с веб-панелью у вас в сети (on-prem).

| Компонент | Версия (сейчас) | Стек |
|-----------|-----------------|------|
| Сервер | **1.10.1** (`VERSION`) | Python 3.11+ FastAPI, Postgres, nginx |
| Агент | **1.3.1** (`agent/VERSION`) | .NET 8, служба Windows, WiX MSI |

| Компонент | Стек |
|-----------|------|
| Deploy | `deploy/debian/install.sh` — установка на Debian 12 |

## С чего начать

**Оператору** (установка сервера, HTTPS, агенты, обновления): **[docs/operator-guide.md](docs/operator-guide.md)**.

**Разработчику** (локальный запуск, тесты): разделы ниже и [docs/agents.md](docs/agents.md).

## Структура репозитория

```
agent/            # служба Windows + CLI bad
server/           # API, панель, зеркало MSI агента
installer/msi/    # WiX (сборка MSI на Windows / GitHub Actions)
deploy/debian/    # install.sh, systemd, nginx
docs/             # гайды и архитектура
VERSION           # версия сервера (не путать с agent/VERSION)
```

## Быстрый старт (сервер, разработка)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DATABASE_URL=postgresql://bad:bad@127.0.0.1:5432/bad
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes

uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/v1/health  
- Панель: http://127.0.0.1:8000/login (`admin` / `admin` при первом запуске — **смените**)  
- Устройства: http://127.0.0.1:8000/devices  

Локальные тесты (если есть untracked `server/tests/`): `pytest -q`

## Агент (разработка)

```bash
cd agent
dotnet build BadAgent.sln -c Release

export BAD_CONFIG_DIR=/tmp/bad-agent-config
export BAD_SERVER_URL=https://bad.example.com
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
dotnet run --project src/BadAgent -c Release
```

В проде на Windows — только **MSI** с `SERVERURL=https://…` и `ENROLLMENTTOKEN=…`. Каталог с `bad` по умолчанию попадает в PATH (`ADDPATH=1`; отключить: `ADDPATH=0`). См. [installer/msi/README.md](installer/msi/README.md).

**CLI на ПК:** любой пользователь — `bad` (текст) и `bad -r` (HTML); настройка — **от администратора**: `bad -c`, `bad config set` / `unset`.

```powershell
BadAgent.exe service status|start|stop|restart   # от администратора
```

Обновления агента: новый MSI публикуется в релизе на GitHub → сервер **сам** скачивает его в зеркало → ПК обновляются **с вашего сервера**, не с GitHub. Подробно: [operator-guide §5](docs/operator-guide.md#5-обновления-агента-upload-msi-и-выбор-версии).

## Документация

| Документ | Для кого |
|----------|----------|
| [docs/operator-guide.md](docs/operator-guide.md) | установка и сопровождение |
| [docs/guideline.md](docs/guideline.md) | правила разработки и релиз MSI |
| [docs/architecture.md](docs/architecture.md) | устройство системы |
| [docs/api-v1.md](docs/api-v1.md) | интеграция (1C Itilium и др.) |
| [docs/agents.md](docs/agents.md) | карта репозитория для разработки |
| [docs/release-notes-1.5.3.md](docs/release-notes-1.5.3.md) | кратко о сервере 1.5.3 |
| [docs/release-notes-1.0.0.md](docs/release-notes-1.0.0.md) · [1.0.1](docs/release-notes-1.0.1.md) | ранние релизы |

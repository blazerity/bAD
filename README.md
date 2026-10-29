# bAD — blazerity Asset Discovery

Лёгкая инвентаризация Windows-компьютеров для локальной сети. Агент собирает данные на ПК, сервер хранит их и показывает в веб-панели. Всё работает on-prem, данные никуда не уходят за пределы вашей инфраструктуры.

[![Версия сервера](https://img.shields.io/badge/server-2.2.2-blue)](VERSION)
[![Версия агента](https://img.shields.io/badge/agent-2.0.2-blue)](agent/VERSION)

## Возможности

- Агент Windows как служба, написан на .NET 8
- Сервер на FastAPI с веб-панелью и API v1
- Установка агента через MSI (WiX)
- Зеркало MSI на сервере: ПК обновляются с вашего сервера, а не с GitHub
- CLI `bad` для пользователей ПК: текстовый и HTML-вывод

## Компоненты

| Компонент | Версия | Стек |
|-----------|--------|------|
| Сервер | 2.2.2 (`VERSION`) | Python 3.11+, FastAPI, PostgreSQL, nginx |
| Агент | 2.0.2 (`agent/VERSION`) | .NET 8, служба Windows, WiX MSI |
| Деплой | — | `deploy/debian/install.sh` (Debian 12) |

## Документация

| Документ | Для кого |
|----------|----------|
| [Руководство оператора](docs/operator-guide.md) | установка, HTTPS, агенты, обновления |
| [Архитектура](docs/architecture.md) | устройство системы |
| [API v1](docs/api-v1.md) | интеграции (например, 1C Itilium) |
| [Агенты и карта репозитория](docs/agents.md) | разработка |
| [Правила разработки и релиз MSI](docs/guideline.md) | разработка и релизы |
| [Release notes](docs/) | [2.2.2](docs/release-notes-2.2.2.md), [2.2.1](docs/release-notes-2.2.1.md), [агент 2.0.2](docs/release-notes-agent-2.0.2.md); архив: [2.2.0](docs/release-notes-2.2.0.md), [2.1.2](docs/release-notes-2.1.2.md) |

Если вы администрируете сервер, начните с [руководства оператора](docs/operator-guide.md).

## Быстрый старт для разработки

### Сервер

Требования: Python 3.11+, PostgreSQL.

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Задайте переменные окружения:

```bash
export BAD_DATABASE_URL=postgresql://bad:bad@127.0.0.1:5432/bad
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes
```

Запустите сервер:

```bash
uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

После запуска доступны:

- Health-check: http://127.0.0.1:8000/v1/health
- Веб-панель: http://127.0.0.1:8000/login (при первом запуске логин и пароль `admin` / `admin`, **обязательно смените их**)
- Список устройств: http://127.0.0.1:8000/devices

Тесты:

```bash
pytest -q
```

### Агент

Требования: .NET 8 SDK.

```bash
cd agent
dotnet build BadAgent.sln -c Release
```

Запуск для разработки:

```bash
export BAD_CONFIG_DIR=/tmp/bad-agent-config
export BAD_SERVER_URL=https://bad.example.com
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b

dotnet run --project src/BadAgent -c Release
```

## Установка агента на Windows

В продакшене агент ставится только через MSI с параметрами `SERVERURL` и `ENROLLMENTTOKEN`:

```powershell
msiexec /i BadAgent.msi SERVERURL=https://bad.example.com ENROLLMENTTOKEN=ваш-токен
```

По умолчанию каталог с `bad` добавляется в `PATH` (`ADDPATH=1`). Чтобы отключить это, передайте `ADDPATH=0`.

Подробнее: [installer/msi/README.md](installer/msi/README.md).

### Управление службой

Выполняется от администратора:

```powershell
bad service status|start|stop|restart
```

Установка (2.0+): `%ProgramFiles%\blazerity\bad agent\`, служба **`badagent`**.

### CLI `bad`

| Команда | Кто может | Что делает |
|---------|-----------|------------|
| `bad` | любой пользователь | текстовый отчёт |
| `bad -r` | любой пользователь | HTML-отчёт |
| `bad -c`, `bad config set`, `bad config unset` | администратор | настройка агента |
| `bad push` | администратор | синхронизация с сервером |
| `bad update` | администратор | проверка и установка MSI с сервера |

## Обновление агента

1. Новый MSI публикуется в релизе на GitHub.
2. Сервер автоматически скачивает его в локальное зеркало.
3. Агенты на ПК обновляются с вашего сервера.

Подробности: [руководство оператора, раздел 5](docs/operator-guide.md#5-обновления-агента-upload-msi-и-выбор-версии).

## Структура репозитория

```
agent/            служба Windows и CLI bad
server/           API, веб-панель, зеркало MSI агента
installer/msi/    WiX: сборка MSI на Windows и в GitHub Actions
deploy/debian/    install.sh, systemd, nginx
docs/             руководства и архитектура
VERSION           версия сервера (не путать с agent/VERSION)
```

## Участие в разработке

Перед отправкой изменений прочитайте [docs/guideline.md](docs/guideline.md). Там описаны правила разработки и релиза MSI.

## Лицензия

TODO: указать лицензию проекта.
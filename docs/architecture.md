# Архитектура bAD

**blazerity Asset Discovery** — Windows-агент инвентаризации и on-prem сервер накопления снимков. Документ описывает фактическую архитектуру репозитория в согласовании с [architecture-plan.md](architecture-plan.md). Версия продукта: **0.2.0**.

## Компоненты

| Компонент | Путь | Роль |
|-----------|------|------|
| **Agent** | `agent/` | .NET 8 Worker Service (`BlazerityAssetDiscovery`): collect → enroll/heartbeat/inventory по HTTPS |
| **Server** | `server/` | FastAPI + SQLite: API `/v1/*`, web UI (session login), uvicorn на `127.0.0.1:8000` |
| **MSI** | `installer/msi/` | WiX: Program Files, служба, public properties `SERVERURL` / `ENROLLMENTTOKEN` |
| **Deploy** | `deploy/debian/` | one-line `install.sh` для Debian 12: venv, systemd, nginx TLS, ufw |

```mermaid
flowchart LR
  subgraph Win["Windows host"]
    SVC["bAD Agent"]
    CFG["ProgramData config"]
    SVC --> CFG
  end
  subgraph Deb["Debian 12"]
    NGX["nginx TLS :443"]
    API["uvicorn FastAPI :8000"]
    DB[("SQLite /var/lib/bad/bad.db")]
    NGX --> API --> DB
  end
  SVC -->|"HTTPS JSON"| NGX
```

## Клиент (агент)

- Установка: MSI → `%ProgramFiles%\blazerity\bAD\`, служба auto-start под LocalSystem.
- Конфиг: `%ProgramData%\blazerity\bAD\config.json` (`server_url`, `enrollment_token` временно, `api_key`, `device_id`, интервалы).
- Жизненный цикл: при старте enroll (если нет API key) → полный inventory → heartbeat каждые 15 мин, inventory каждые 6 ч.
- `device_id`: MachineGuid (registry), fallback SMBIOS UUID.
- Collectors: WMI/CIM + .NET; сбой секции → `null` + запись в `collector_errors[]`.
- HTTPS only; cleartext `http://` отклоняется (кроме явного `BAD_ALLOW_HTTP=1` для локальной разработки).
- `User-Agent: bad-agent/<semver>`; в payload поле `agent_version`.

## Сервер

### API (`/v1`)

| Method | Path | Auth | Назначение |
|--------|------|------|------------|
| `GET` | `/v1/health` | нет | liveness + `version` |
| `POST` | `/v1/enroll` | enrollment Bearer | обмен на per-agent API key |
| `POST` | `/v1/heartbeat` | API key | `last_seen`, `agent_version` |
| `POST` | `/v1/inventory` | API key | upsert снимка по `device_id` |
| `GET` | `/v1/devices` | **admin Bearer only** | список устройств |
| `GET` | `/v1/devices/{device_id}` | **admin Bearer only** | meta + последний inventory |

- `schema_version` сейчас `1`; неизвестные версии → `400`.
- Секреты сайта: enrollment и admin tokens (разные); в БД хранятся hash (argon2).
- Admin API token — только `Authorization: Bearer` (автоматизация). Web-сессия на `/v1/*` не действует.
- Rate limit на `/v1/enroll` (sliding window).
- Retention: последние 30 снимков на устройство.

### TLS и nginx

- nginx слушает 443, TLS 1.2+, HSTS; proxy на `http://127.0.0.1:8000`.
- uvicorn не публикует внешний интерфейс.
- Cert/key: пути при install → symlink в `/etc/bad/tls/`.

### Web UI и аутентификация

| Path | Назначение |
|------|------------|
| `/login` | username/password (local, затем LDAP если включён) |
| `/logout` | сброс cookie сессии |
| `/devices`, `/devices/{id}` | read-only просмотр; требуют session cookie `bad_session` |
| `/settings/ldap` | CRUD LDAP + Test connection; только role `admin` |
| `/account/password` | смена пароля локального пользователя |

**Локальные пользователи**

- Таблица `local_users`; пароли — argon2.
- Первый boot / пустая таблица: создаётся `admin` / `admin` с флагом `must_change_password` (баннер + редирект на смену пароля).
- Работает **без** настроенного LDAP.

**LDAP (опционально)**

- Настройки в `ldap_settings` (одна строка): host, port, use_ssl / start_tls, bind DN, encrypted bind password, search base, filter template (`{username}`), display name attr, default role.
- Bind password шифруется Fernet-ключом из `site_secrets.data_key`; в форме после save — placeholder «unchanged», plaintext не отдаётся.
- Логин: сначала local match; иначе, если LDAP enabled — search + user bind через `ldap3`.
- Роль LDAP-пользователей: `operator` (devices) или `admin` (включая LDAP settings) — поле default role.

**Сессия**

- Подписанный cookie `bad_session` (itsdangerous, 12h); секрет из `BAD_SESSION_SECRET` или `site_secrets.session_secret`.

### Данные

- SQLite: `/var/lib/bad/bad.db` (prod), владелец `bad:bad`, режим ideally `0600`, WAL.
- Таблицы: `devices`, `inventory_snapshots`, `site_secrets`, `local_users`, `ldap_settings`.
- Миграции: `server/bad_server/migrations/` (`001_initial.sql`, `002_web_auth.sql`); runtime применяет schema в `Database._init_schema`.

## Enrollment и inventory

1. Оператор задаёт site enrollment token (install script → `/etc/bad/site.env`).
2. MSI/config передаёт `SERVERURL` + `ENROLLMENTTOKEN`.
3. Агент `POST /v1/enroll` → получает `api_key`, сохраняет в ProgramData, затирает enrollment token.
4. Повторные запуски используют API key; upsert по стабильному `device_id`.

## Deploy

```bash
BAD_DOMAIN=… BAD_TLS_CERT=… BAD_TLS_KEY=… sudo -E bash deploy/debian/install.sh
```

Скрипт: пакеты, user `bad`, `/opt/bad` + venv, `bad-api.service`, nginx site, ufw 22/80/443, печать enrollment/admin tokens один раз. Web UI после install: `admin`/`admin` (сменить сразу); admin Bearer token — для API/автоматизации.

Артефакты релиза (имена): `bad-agent-<semver>.msi`, `bad-server-<semver>.tar.gz`, `install.sh`.

## Вне scope v1 / ещё не сделано

macOS/Linux агенты, software inventory, полноценный RBAC/SSO/группы AD, HA SQLite, push-команды на агент, Let’s Encrypt как основной путь, product dashboard.

# bAD Server

Сервис на Python 3.11+ FastAPI + **Postgres** для blazerity Asset Discovery.

## Локальная разработка

Нужен Postgres (docker/local) и `BAD_DATABASE_URL`.

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DATABASE_URL=postgresql://bad:bad@127.0.0.1:5432/bad
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes

# Только localhost (как в проде за nginx)
uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

- Health: `http://127.0.0.1:8000/v1/health`
- Web UI: `http://127.0.0.1:8000/login` (локальный `admin`/`admin` при первом запуске; опционально LDAP через `/settings/ldap`)
- Admin API token (`BAD_ADMIN_TOKEN`) — только Bearer для `/v1/devices*`, не для входа в браузере

## Стенд QA и скриншоты панели

Для съёмки UI на `http://127.0.0.1:8000` без баннера HTTP, мастера «первый запуск» и редиректа на смену пароля:

```bash
export BAD_QA_UI=1
# … BAD_DATABASE_URL и прочие переменные как выше
uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

Вход: `admin` / `admin` (как при первом запуске). **Не задавайте `BAD_QA_UI` в production** — при старте в лог пишется предупреждение.

Что отключается при `BAD_QA_UI=1`:

- баннер «сайт без защищённого соединения» и блокировка полей в Параметрах из‑за `tls_mode=http`;
- редирект и урезанное меню при `must_change_password` (пароль по умолчанию можно не менять для скринов);
- чеклист/мастер первого запуска на Обзоре и пункты «сменить пароль / нужен HTTPS» в ленте «требует действия»;
- `sensitive_over_http_blocked` для LDAP/SMTP/бэкапов/site-bundle (как `BAD_ALLOW_SENSITIVE_OVER_HTTP=1`).

Агентский transport (HTTPS-only, enroll по HTTP при managed TLS) **не** меняется — для enroll по HTTP см. `BAD_ALLOW_ENROLL_OVER_HTTP` / `BAD_ALLOW_HTTP` на агенте.

Демо-парк (6 ПК, inventory schema v2, `network.nics`, CPU для дашборда):

```bash
cd server
python scripts/seed-beta-demo.py --base http://127.0.0.1:8000 --token "$BAD_ENROLLMENT_TOKEN"
```

Повторный запуск перезапишет те же `device_id` (enroll для уже существующих устройств).

## Тесты

Unit tests лежат в `server/tests/` **только локально** (gitignored, не в GitHub). CI pytest не запускает.

```bash
cd server
pytest -q   # нужен локальный untracked каталог tests/
```

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

## Тесты

Unit tests лежат в `server/tests/` **только локально** (gitignored, не в GitHub). CI pytest не запускает.

```bash
cd server
pytest -q   # нужен локальный untracked каталог tests/
```

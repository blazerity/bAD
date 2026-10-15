# bAD Server

Python 3.11+ FastAPI + SQLite service for blazerity Asset Discovery.

## Local development

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

export BAD_DB_PATH=./data/bad.db
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ADMIN_TOKEN=dev-admin-token-change-me-please-32bytes

# Bind localhost only (as in production behind nginx)
uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

- Health: `http://127.0.0.1:8000/v1/health`
- Web UI: `http://127.0.0.1:8000/login` (admin token)

## Tests

```bash
cd server
pytest -q
```

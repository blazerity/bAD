# Сервер

Панель и API. Python 3.11+, PostgreSQL, переменная `BAD_DATABASE_URL`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

Панель: http://127.0.0.1:8000/login . Первый локальный вход: `admin` / `admin`.

Флаги `BAD_ALLOW_SHARED_ENROLLMENT` и `BAD_REQUIRE_INVENTORY_SIGNATURE` те же, что флажки в **Параметры → Обновления агента**. Как их включить — [docs/ste-100.md](../docs/ste-100.md).

# Сервер

Панель и API. Python 3.11+, PostgreSQL, переменная `BAD_DATABASE_URL`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn bad_server.app:app --host 127.0.0.1 --port 8000
```

Панель: http://127.0.0.1:8000/login . Первый локальный вход: `admin` / `admin`.

Флажки регистрации и подписи снимка — в **Параметры → Обновления агента**. Порядок — [docs/ste-100.md](../docs/ste-100.md).

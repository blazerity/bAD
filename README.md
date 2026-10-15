# bAD — blazerity Asset Discovery

Lightweight Windows inventory agent + on-prem accumulation server.

| Component | Stack |
|-----------|--------|
| Agent | .NET 8 Worker Service (Windows Service), WiX MSI |
| Server | Python 3.11+ FastAPI + SQLite, uvicorn behind nginx TLS |
| Deploy | `deploy/debian/install.sh` one-line install on Debian 12 |

## Repository layout

```
agent/            # C# Worker Service + unit tests
server/           # FastAPI app, web UI, pytest
installer/msi/    # WiX sources (build on Windows)
deploy/debian/    # install.sh, systemd, nginx template
docs/             # operator guide
```

## Quick start (server on Linux)

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
- Web UI (admin token): http://127.0.0.1:8000/login  
- Devices: http://127.0.0.1:8000/devices  

```bash
pytest -q
```

## Agent (dev)

```bash
cd agent
dotnet build BadAgent.sln -c Release
dotnet test BadAgent.sln -c Release

# Point at a local server (HTTP only with explicit opt-in):
export BAD_CONFIG_DIR=/tmp/bad-agent-config
export BAD_SERVER_URL=http://127.0.0.1:8000
export BAD_ENROLLMENT_TOKEN=dev-enrollment-token-change-me-please-32b
export BAD_ALLOW_HTTP=1
dotnet run --project src/BadAgent -c Release
```

On Windows, install as a service via the MSI (`installer/msi/`) with public properties `SERVERURL` and `ENROLLMENTTOKEN`.

## Operator path

See [docs/operator-guide.md](docs/operator-guide.md): Debian one-line install → MSI → device appears in the HTTPS web UI.

## Architecture

Locked plan: [docs/architecture-plan.md](docs/architecture-plan.md) (copied from project planning). Decisions in that document are not reopened for MVP.

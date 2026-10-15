# bAD — blazerity Asset Discovery

Lightweight Windows inventory agent + on-prem accumulation server.

| Component | Stack |
|-----------|--------|
| Agent | .NET 8 Worker Service (Windows Service), WiX MSI |
| Server | Python 3.11+ FastAPI + SQLite, uvicorn behind nginx TLS |
| Deploy | `deploy/debian/install.sh` one-line install on Debian 12 |

## Repository layout

```
agent/            # C# Worker Service + unit tests + service CLI
server/           # FastAPI app, web UI, agent-update mirror, pytest
installer/msi/    # WiX sources (MSI built on Windows / GHA release-msi)
deploy/debian/    # install.sh, systemd, nginx template
docs/             # architecture, guidelines, agent notes, operator guide
VERSION           # product semver (0.4.0)
.github/workflows # ci.yml (Linux) + release-msi.yml (Windows tags)
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
- Web UI: http://127.0.0.1:8000/login (default `admin` / `admin` on first boot — change it)  
- Devices: http://127.0.0.1:8000/devices  
- LDAP settings (admin): http://127.0.0.1:8000/settings/ldap  


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

Service control (elevated):

```powershell
BadAgent.exe service status|start|stop|restart
```

Self-update: agents poll the **server** (not GitHub) for a newer mirrored MSI; see [docs/architecture.md](docs/architecture.md).

## Releases (agent MSI)

Tag `v0.4.0` (or run `release-msi` manually) → Windows GHA builds MSI + `agent-release.json` → GitHub Release → server sync → agents upgrade. Linux CI does **not** build MSI. Details: [docs/guideline.md](docs/guideline.md).

## Docs

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | Архитектура + web LDAP auth + pipeline обновления агента |
| [docs/guideline.md](docs/guideline.md) | Инженерные правила + как релизить MSI |
| [docs/agents.md](docs/agents.md) | Агент, service CLI, version bump, LDAP/web auth map, инварианты |
| [docs/operator-guide.md](docs/operator-guide.md) | Операторский путь: Debian install → MSI → web UI |
| [docs/architecture-plan.md](docs/architecture-plan.md) | Locked plan v1 (решения не переоткрывать для MVP) |

## Operator path

See [docs/operator-guide.md](docs/operator-guide.md): Debian one-line install → MSI → device appears in the HTTPS web UI.

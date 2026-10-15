# Operator guide — bAD

End-to-end path: install server → install Windows agent MSI → see the device in the web UI.

## 1. Server (Debian 12)

Prepare a TLS certificate and key whose CN/SAN matches the public DNS name.

```bash
# From a release tarball or git checkout that contains deploy/debian + server/
BAD_DOMAIN=bad.example.com \
BAD_TLS_CERT=/etc/ssl/certs/bad.fullchain.pem \
BAD_TLS_KEY=/etc/ssl/private/bad.privkey.pem \
  sudo -E bash deploy/debian/install.sh
```

The script prints (once):

- `https://bad.example.com/`
- enrollment token (agent MSI)
- admin API token (Bearer automation)

Verify:

```bash
curl -fsS https://bad.example.com/v1/health
# → {"status":"ok","version":"0.8.0"}
```

### Web login (local)

1. Open `https://bad.example.com/login`
2. Sign in with the default local account: **`admin` / `admin`**
3. Change the password immediately (`Password` in the header, or the forced redirect)

This works with **no LDAP configured**. The admin API token is **not** used for the browser UI.

Tokens live in `/etc/bad/site.env` (mode `640`, `root:bad`). uvicorn listens on `127.0.0.1:8000` only; nginx terminates TLS on 443.

### Optional: LDAP from the UI

1. Sign in as a local **admin**
2. Open **LDAP** (`/settings/ldap`)
3. Fill host, port, SSL/StartTLS, bind DN + bind password, user search base, filter template (must include `{username}`), display name attribute, default role
4. **Save settings**, then **Test connection**
5. Enable LDAP login; directory users can sign in on `/login` (local users are tried first)

Bind passwords are stored encrypted in SQLite and never shown again after save (leave the field blank to keep unchanged).

Security caveat: change the default `admin`/`admin` password before exposing the UI beyond a trusted network.

## 2. Windows agent (MSI)

On a Windows build host, produce the MSI (see `installer/msi/README.md`), then install:

```powershell
msiexec /i bad-agent-0.8.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  /qn
```

Optional PATH for local `bad` CLI (default off):

```powershell
msiexec /i bad-agent-0.8.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  ADDPATH=1 `
  /qn
```

The service `BlazerityAssetDiscovery` starts automatically, enrolls once, stores the API key under `%ProgramData%\blazerity\bAD\config.json`, and sends inventory on start (then every 6 hours) with heartbeats every 15 minutes. It also checks the server for MSI updates (never GitHub directly). Local CLI (no server needed): `bad` / `bad -h` / `bad -?`. Service CLI: `BadAgent.exe service status|start|stop|restart` (elevated). See [agents.md](./agents.md).

## 3. Confirm in the web UI

1. Open `https://bad.example.com/devices` (after signing in)
2. Find the hostname (health badge: **OK** if last seen within the stale threshold, else **stale**)
3. Open the device page to view tags, recent change events, and the latest inventory JSON
4. Optional: open **Events** (`/events`) for a newest-first change log across devices

Tags: edit on the device page (comma-separated). Filter the devices list by tag. Policies can also match `tag equals/contains`.

Stale threshold defaults to 1 hour (`BAD_DEVICE_STALE_AFTER_SECONDS`); set ≈2× heartbeat if you prefer (e.g. `1800` for a 15‑minute heartbeat). Product version **0.8.0**.

Alternatively (automation — admin API token):

```bash
curl -fsS -H "Authorization: Bearer <admin-token>" \
  https://bad.example.com/v1/devices
curl -fsS -H "Authorization: Bearer <admin-token>" \
  'https://bad.example.com/v1/events?limit=50'
```

## Notes

- MSI upgrades keep ProgramData (API key); re-enrollment is not required.
- Do not put enrollment or admin tokens in world-readable files.
- Local demos without TLS: run uvicorn on Linux (`server/README.md`) and point a test agent with `BAD_ALLOW_HTTP=1` at `http://127.0.0.1:8000`.

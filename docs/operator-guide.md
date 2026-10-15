# Operator guide — bAD MVP

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
- enrollment token
- admin token

Verify:

```bash
curl -fsS https://bad.example.com/v1/health
# → {"status":"ok"}
```

Open `https://bad.example.com/login` and sign in with the **admin token**.

Tokens live in `/etc/bad/site.env` (mode `640`, `root:bad`). uvicorn listens on `127.0.0.1:8000` only; nginx terminates TLS on 443.

## 2. Windows agent (MSI)

On a Windows build host, produce the MSI (see `installer/msi/README.md`), then install:

```powershell
msiexec /i bad-agent-1.0.0.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  /qn
```

The service `BlazerityAssetDiscovery` starts automatically, enrolls once, stores the API key under `%ProgramData%\blazerity\bAD\config.json`, and sends inventory on start (then every 6 hours) with heartbeats every 15 minutes.

## 3. Confirm in the web UI

1. Open `https://bad.example.com/devices`
2. Find the hostname
3. Open the device page to view the latest inventory JSON

Alternatively:

```bash
curl -fsS -H "Authorization: Bearer <admin-token>" \
  https://bad.example.com/v1/devices
```

## Notes

- MSI upgrades keep ProgramData (API key); re-enrollment is not required.
- Do not put enrollment or admin tokens in world-readable files.
- Local demos without TLS: run uvicorn on Linux (`server/README.md`) and point a test agent with `BAD_ALLOW_HTTP=1` at `http://127.0.0.1:8000`.

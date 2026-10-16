# bAD API `/v1` — интеграционный гайд (1C Itilium и др.)

Стабильный HTTP JSON API on-prem сервера bAD. Версия продукта на момент заморозки документации: **0.12.x** (`GET /v1/health` → `version`).

**Политика совместимости (additive freeze):** путь `/v1` заморожен как **additive**. Можно добавлять необязательные поля, query-параметры с default и новые эндпоинты. **Breaking** (удаление/переименование полей, смена смысла, обязательность новых полей, смена кодов ошибок для существующих сценариев) — только по явному решению владельца продукта. Клиенты (в т.ч. **1C Itilium**) должны игнорировать неизвестные JSON-поля.

Связанные документы: [architecture.md](architecture.md) · [operator-guide.md](operator-guide.md) · [guideline.md](guideline.md). Allowlist knobs политик (тема C): Project store `internal/policies-knobs-contract.md`.

---

## 1. Base URL и транспорт

| Среда | Base URL (пример) |
|-------|-------------------|
| Prod (nginx TLS) | `https://bad.example.com` |
| Lab (uvicorn local) | `http://127.0.0.1:8000` |

Все пути ниже — относительно base, с префиксом `/v1/...`.

- **JSON:** `Content-Type: application/json` (тела POST/PUT).
- **Auth:** заголовок `Authorization: Bearer <token>` (кроме `GET /v1/health`).
- **TLS:** в бою — только HTTPS. OpenAPI UI в production отключён (`docs_url=None`).
- **Не путать** web-сессию (`bad_session` cookie) с admin Bearer: UI login **не** даёт admin API token.

Токен admin печатается при `deploy/debian/install.sh` (файл `/etc/bad/site.env`, переменная `BAD_ADMIN_TOKEN`) или задаётся env `BAD_ADMIN_TOKEN` в lab.

---

## 2. Три механизма auth (не смешивать)

| Механизм | Header | Для кого | Типичное использование |
|----------|--------|----------|------------------------|
| **Admin Bearer** | `Authorization: Bearer <admin_token>` | внешние системы (**1C Itilium**), автоматизация | чтение устройств/inventory/events; policies; revoke/archive |
| **Agent API key** | `Authorization: Bearer <bad_ak_…>` | Windows-агент | enroll→key; heartbeat; inventory; agent config/update |
| **Enrollment Bearer** | `Authorization: Bearer <site_enrollment>` | только первый обмен агента | `POST /v1/enroll` |

Web UI (local/LDAP session) — **не** контракт для 1C.

---

## 3. Что для 1C / внешней системы, что только для агента

### Рекомендуется для 1C Itilium (admin Bearer)

| Method | Path | Назначение |
|--------|------|------------|
| `GET` | `/v1/health` | liveness + `version` (без auth) |
| `GET` | `/v1/devices` | список устройств (пагинация, фильтры) |
| `GET` | `/v1/devices/{device_id}` | карточка + **latest inventory** |
| `GET` | `/v1/events` | лента изменений inventory |
| `GET` | `/v1/admin/devices/{device_id}/config` | effective settings + `sources` (опционально) |
| `GET` | `/v1/admin/policies` | список политик (опционально) |
| `GET` | `/v1/admin/agent-update` | статус зеркала MSI (опционально) |

Опционально (мутации — осознанно, не для read-only выгрузки):

| Method | Path | Заметка |
|--------|------|---------|
| `PUT` | `/v1/devices/{device_id}/tags` | заменить теги |
| `POST` | `/v1/devices/{device_id}/archive` / `restore` | скрыть/вернуть |
| `POST` | `/v1/devices/{device_id}/revoke` | отозвать agent key |
| `POST` | `/v1/devices/{device_id}/rotate-key` | новый key (**plaintext один раз** — не логировать) |
| `DELETE` | `/v1/devices/{device_id}` | hard-delete |
| `GET/POST/PUT/DELETE` | `/v1/admin/policies*` | CRUD политик |
| `PUT/DELETE` | `/v1/admin/devices/{id}/config-override` | server override |
| `POST` | `/v1/admin/enrollment/rotate` | plaintext enrollment token один раз — **только HTTPS** |
| `POST` | `/v1/admin/agent-update/sync` | sync зеркала |

### Только для агента (не вызывать из 1C)

| Method | Path | Auth |
|--------|------|------|
| `POST` | `/v1/enroll` | enrollment |
| `POST` | `/v1/heartbeat` | agent key |
| `POST` | `/v1/inventory` | agent key |
| `GET` | `/v1/agent/config` | agent key |
| `GET` | `/v1/agent/update/check` | agent key |
| `GET` | `/v1/agent/update/msi` | agent key |

---

## 4. Ошибки

Формат FastAPI/HTTPException:

```json
{ "detail": "краткое сообщение" }
```

иногда `detail` — массив валидации Pydantic.

| HTTP | Когда (типично) |
|------|------------------|
| `400` | плохой body / `Unsupported schema_version: N` / невалидные policy settings |
| `401` | нет/неверный Bearer (admin / agent key / enrollment) |
| `403` | revoked API key; `device_id mismatch`; cleartext enroll при managed TLS |
| `404` | устройство / политика / MSI не найдены |
| `409` | re-enroll без proof / устройство уже enrolled |
| `429` | rate limit на `/v1/enroll` |
| `502` | сбой GitHub sync (admin sync) |

Клиент 1C: при `401` — проверить admin token; при `404` на device — устройство удалено/не enroll’ено; неизвестные поля в успешном JSON **игнорировать**.

---

## 5. Пагинация и фильтры

### `GET /v1/devices`

| Query | Default | Описание |
|-------|---------|----------|
| `page` | `1` | страница, ≥ 1 |
| `page_size` | `50` | 1…200 |
| `tag` | — | точное совпадение тега (case-insensitive) |
| `q` | — | подстрока в `device_id` / `hostname` / `meta.serial_number` |
| `archived` | `false` | `true` — только архив |

Ответ:

```json
{
  "devices": [ /* см. §6 */ ],
  "total": 123,
  "page": 1,
  "page_size": 50
}
```

Обход всех устройств: `page=1…ceil(total/page_size)`.

### `GET /v1/events`

| Query | Default | Описание |
|-------|---------|----------|
| `device_id` | — | фильтр |
| `limit` | `100` | 1…500 |
| `offset` | `0` | смещение |

Ответ: `{ "events": [...], "total", "limit", "offset" }`.

---

## 6. Устройства (admin)

### Элемент списка (`GET /v1/devices`)

```json
{
  "device_id": "…",
  "hostname": "WS-01",
  "enrolled_at": "2026-10-01T10:00:00Z",
  "last_seen_at": "2026-10-16T11:00:00Z",
  "agent_version": "0.12.0",
  "meta": {
    "last_inventory_at": "…",
    "os": "Microsoft Windows 11 …",
    "serial_number": "…",
    "last_inventory_ok": true
  },
  "tags": ["wave-1"],
  "revoked": false,
  "archived": false
}
```

`meta` — произвольный JSON объекта (health, `config_local`, …). Новые ключи additive.

### Карточка (`GET /v1/devices/{device_id}`)

Поля списка **плюс**:

| Поле | Описание |
|------|----------|
| `serial_number` / `model` | удобные извлечения из latest hardware |
| `latest_inventory` | `{ id, received_at, schema_version, payload }` или `null` |
| `duplicates` | подсказки возможных дублей |

`latest_inventory.payload` — тот же снимок, что агент POST’ит на `/v1/inventory` (см. §7).

---

## 7. Inventory schema

Сервер принимает `schema_version` ∈ `{1, 2}` (`Settings.known_schema_versions`). Иное → `400`.

| Version | Заметка |
|---------|---------|
| `1` | host / network / hardware / users; без обязательного software |
| `2` | + optional `software`; hardware fields (`serial_number`, `gpus`, `ram_modules`, …) **additive** без bump |

Типичный `payload` (сокращённо):

```json
{
  "schema_version": 2,
  "device_id": "…",
  "collected_at": "2026-10-16T11:00:00Z",
  "agent_version": "0.12.0",
  "host": {
    "hostname": "WS-01",
    "domain": "CONTOSO",
    "ad_ou": "OU=Laptops,OU=Workstations,DC=contoso,DC=com",
    "ad_distinguished_name": "CN=WS-01,…",
    "os": { "caption": "…", "version": "…", "build": "…" }
  },
  "hardware": {
    "serial_number": "…",
    "model": "…",
    "manufacturer": "…",
    "cpu": "…",
    "ram_bytes": 17179869184,
    "disks": [],
    "volumes": [],
    "gpus": [],
    "ram_modules": [],
    "monitors": [],
    "battery": {}
  },
  "network": { "nics": [] },
  "users": { "logged_on": [], "last_interactive": null },
  "software": { "items": [] },
  "minidumps": { "count": 0, "files": [] },
  "collector_errors": []
}
```

Неизвестные поля в payload сервер сохраняет (`extra` allow). Для 1C: читать нужные ключи; отсутствие optional-секции = коллектор выключен / soft-fail (`null` / omit), смотреть `collector_errors`.

---

## 8. Примеры curl (1C / автоматизация)

Подставьте `BASE` и `ADMIN`.

```bash
BASE=https://bad.example.com
ADMIN='…from site.env BAD_ADMIN_TOKEN…'

# Health
curl -sS "$BASE/v1/health"

# Список устройств (первая страница)
curl -sS -H "Authorization: Bearer $ADMIN" \
  "$BASE/v1/devices?page=1&page_size=50"

# Поиск / фильтр
curl -sS -H "Authorization: Bearer $ADMIN" \
  "$BASE/v1/devices?q=WS-01&tag=wave-1"

# Карточка + latest inventory
curl -sS -H "Authorization: Bearer $ADMIN" \
  "$BASE/v1/devices/DEVICE_ID_HERE"

# События изменений
curl -sS -H "Authorization: Bearer $ADMIN" \
  "$BASE/v1/events?limit=100&offset=0"

# Effective config + provenance sources
curl -sS -H "Authorization: Bearer $ADMIN" \
  "$BASE/v1/admin/devices/DEVICE_ID_HERE/config"
```

PowerShell (1C часто рядом с Windows):

```powershell
$h = @{ Authorization = "Bearer $env:BAD_ADMIN_TOKEN" }
Invoke-RestMethod -Uri "https://bad.example.com/v1/devices?page=1" -Headers $h
```

Рекомендуемый цикл выгрузки в Itilium:

1. `GET /v1/health` — доступность и версия API-сервера.  
2. Листать `GET /v1/devices` до исчерпания `total`.  
3. Для каждого (или по дельте `last_seen_at`) — `GET /v1/devices/{id}` и разобрать `latest_inventory.payload`.  
4. Опционально догонять `GET /v1/events` для изменений без полного inventory.

Не кладите admin token в URL query, логи 1C или публичные обработки.

---

## 9. Policies / config (кратко)

Remote merge: **defaults < matching policies (priority asc) < device_override**.  
UI provenance на ключ: `default` | `policy` | `device_override` | `agent_local` (см. [architecture.md — config source](architecture.md#api-notes-config-source-provenance)).

Allowlist knobs и условия политик — в Project `internal/policies-knobs-contract.md` (тема C). Не пушить `server_url` / секреты через policies.

`GET /v1/admin/devices/{id}/config` возвращает в т.ч.:

```json
{
  "effective": {},
  "sources": { "collect_software": "policy" },
  "agent_local_keys": [],
  "has_agent_local": false,
  "matched_policies": [],
  "override": null,
  "version": "…"
}
```

---

## 10. Agent-only (справка, не для 1C)

| Endpoint | Заметка |
|----------|---------|
| `POST /v1/enroll` | body: `device_id`, optional `hostname`, `agent_version`, `current_api_key`; ответ `{ api_key, device_id }` |
| `POST /v1/heartbeat` | health + optional `config_local`; piggyback `config` если `config_version` устарел |
| `POST /v1/inventory` | upsert снимка; ответ `{ status, snapshot_id }` |
| `GET /v1/agent/config` | effective settings своего устройства |
| `/v1/agent/update/*` | self-update MSI |

Cleartext enroll при активном managed TLS → `403` с `detail` про HTTPS (`BAD_ALLOW_ENROLL_OVER_HTTP=1` только lab).

---

## 11. Заморозка и эволюция

| Разрешено без breaking-решения | Требует решения владельца |
|--------------------------------|---------------------------|
| Новые optional поля в ответах | Удаление/rename полей |
| Новые эндпоинты `/v1/...` | Смена auth модели |
| Новый `schema_version` inventory + поддержка старых | Обязательные новые поля в существующих request |
| Расширение allowlist knobs (документировать) | Сужение allowlist / ужесточение валидации ломающее старых клиентов |

Код роутера: `server/bad_server/api.py` (префикс `/v1`). При изменении публичного контракта — обновить этот файл и тесты.

# Руководства по разработке bAD

Краткие инженерные правила для этого репозитория. Стек, границы и update pipeline: [architecture.md](architecture.md).

## Общие принципы

- **Thin agent**: агент только собирает и POST’ит; бизнес-логика и хранение — на сервере.
- **Idempotent upsert**: стабильный `device_id`; повторная отправка безопасна.
- **Least privilege / secrets**: TLS везде; секреты не вшивать в MSI binary; не логировать tokens/API keys.
- **MVP scope**: не раздувать web UI, роли, плагины, cloud control plane.
- **Updates via server**: агенты качают MSI только с on-prem API; GitHub — источник для серверного зеркала.

## API

- Префикс версионирования пути: `/v1/...`.
- **Additive freeze `/v1`:** breaking только по решению владельца. Интеграционный гайд (1C Itilium): [api-v1.md](api-v1.md).
- JSON, `Content-Type: application/json`, `Authorization: Bearer <token>`.
- Разделять enrollment token, agent API key и admin token.
- Ошибки: осмысленный HTTP status + краткий `detail`; неизвестный `schema_version` → `400`.
- Не включать OpenAPI UI в production (`docs_url=None` уже так).
- Новые поля в inventory — обратно совместимо внутри `schema_version=1` или новый integer schema с явной поддержкой на сервере.
- Update endpoints: agent key на `/v1/agent/update/*`; admin на `/v1/admin/agent-update*`.
- Remote config: agent key только на `GET /v1/agent/config` (и piggyback в heartbeat); мутации policies/overrides — admin session/token. Только allowlisted knobs, без shell/команд.

## Безопасность

- Агент отклоняет `http://` без явного opt-in для dev.
- На сервере: hash секретов (argon2); site.env `640` root:bad; каталог бэкапов — как секреты (`700` / файлы `600`).
- **SEC-005:** keys в `/etc/bad/data_key` + `session_secret`; **dump/daily DB ≠ ключи** (`pg_dump -Fc`). Site bundle = `bad.dump`+keys; key escrow отдельно. Legacy keys в `site_secrets` → dump = компромисс. [operator-guide.md](operator-guide.md#безопасность-для-операторов).
- **БД:** только Postgres через `BAD_DATABASE_URL` (без URL API не стартует). Local PG при install — localhost. HA/ACME — не обещать.
- **SEC-011:** MSI write-config не кладёт token в argv PowerShell (HKLM Setup); residual — `msiexec … ENROLLMENTTOKEN=` / verbose logs — не пересылать; **после массовой установки MSI смена enrollment-токена обязательна** ([operator-guide.md](operator-guide.md#ротация-enrollment-token-после-массовой-установки-msi)).
- **SEC-003:** LDAP TLS — по умолчанию `CERT_REQUIRED`; lab opt-in `tls_insecure` только для лаборатории, не для боя.
- После install **сразу** сменить `admin`/`admin` (`/account/password`); до смены UI пускает только `/account/password` и `/logout` (навигация скрыта).
- Cookie `bad_session`: `BAD_COOKIE_SECURE=auto`; **инвариант panel-first:** cert из UI (`/settings/tls`) — канон; `BAD_TLS_*` при install опциональны; агенты только HTTPS (кроме lab). Risk HTTP-окна **Medium** при runbook ([чеклист](operator-guide.md#чеклист-окна-http-bootstrap)). ACME не обещать.
- uvicorn не наружу.
- nginx rate-limit / app enroll limiter — сохранять и ужесточать осторожно.
- ProgramData ACL: Administrators + SYSTEM; не world-readable.
- Логи (Serilog / journald): без plaintext tokens и API keys (включая `BAD_GITHUB_TOKEN` и enrollment).

## Логирование

- Сервер: структурированно через стандартный logging / journalctl unit `bad-api`.
- Агент: Serilog file sink под `%ProgramData%\blazerity\bAD\logs\` (ротация ~7 дней); msiexec log рядом при upgrade.
- Сообщения — actionable (enroll failed, backoff, update sha mismatch), без секретов.

## Версионирование (две линии)

| Линия | Канон | Tags |
|-------|-------|------|
| **Server** | корневой `VERSION` | `server-vX.Y.Z` |
| **Agent** | `agent/VERSION` (+ csproj / MSI) | `agent-vX.Y.Z` (переходно голый `v*` = agent) |

- Bump (обе): **patch** hotfix / **minor** feature / **major** — только владелец. Checklist: [agents.md](agents.md).
- Агент стабилен → можно держать agent patch-line ([`agent/VERSION`](../agent/VERSION)) и бампать только сервер ([`VERSION`](../VERSION)) без нового MSI.
- **Не путать:** **Обновление сервера** (server) ≠ **Обновления агента** / «Собрать MSI» (agent semver в `workflow_dispatch.version`).
- `schema_version` inventory — integer, третья ось. Агент шлёт `agent_version`; `/v1/health` → `version` = **server**.

## Как вырезать релиз агента (MSI)

1. Bump **agent** line ([`agent/VERSION`](../agent/VERSION) + csproj / WiX) — не корневой [`VERSION`](../VERSION); checklist в [agents.md](agents.md).
2. Тег и push (`VER` = содержимое `agent/VERSION`):
   ```bash
   VER=$(tr -d '[:space:]' < agent/VERSION)
   git tag "agent-v${VER}"
   git push origin "agent-v${VER}"
   ```
   (переходно ещё принимают голый `v*` = agent, пока CI на `v*`.)
3. Workflow **`release-msi`** (`windows-latest`): publish agent → WiX v5 → GitHub Release assets `bad-agent-<версия из agent/VERSION>.msi` + `agent-release.json`. Semver: input `version` > tag > `agent/VERSION`; **не** читать server `VERSION`.
4. Права: `contents: write`. Для public repo достаточно `GITHUB_TOKEN`. Private / panel — `BAD_GITHUB_TOKEN` на сервере.
5. На сервере: фоновая синхронизация, `POST /v1/admin/agent-update/sync`, загрузка MSI в панели или кнопка сборки на GitHub — файл попадает в **зеркало на сервере**.
6. Агенты на ПК проверяют зеркало при старте службы и по расписанию (по умолчанию раз в 24 ч), либо после `BadAgent.exe service restart`.

**Не обещать**: что MSI уже собирается в Linux CI — нет. Server-tag **`server-v*`** MSI не публикует.

Ручной запуск: Actions → `release-msi` → `workflow_dispatch` (поле `version` = agent).

## Зеркало на сервере

В `/etc/bad/site.env`:

```bash
BAD_GITHUB_REPO=blazerity/bAD
BAD_AGENT_UPDATES_DIR=/var/lib/bad/agent-updates
BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS=3600
BAD_AGENT_UPDATE_SYNC_ON_STARTUP=true
# BAD_GITHUB_TOKEN=...   # private repo + panel server-update / Actions MSI
#   scopes: contents:read; для «Собрать MSI» — actions:write
# BAD_GITHUB_TOKEN_FILE=/etc/bad/github_token   # опц. файл 440
BAD_BACKUP_DIR=/var/lib/bad/backups
# BAD_BACKUP_INTERVAL_SECONDS=3600
```

## Web UI (admin)

Единый раздел. Не плодить противоречащие описания «без дашборда» — обзорная сводка есть, marketing landing нет.

- **Язык / look**: Windows 11 / Fluent light, русский UI; `static/style.css`, favicon; stroke-иконки секций; HTML-отчёт CLI в той же семье токенов.
- **Обзор** `/` (`/overview`): totals (активные / онлайн / устарели / архив), breakdown версий агента, последние события железа.
- **Устройства** `/devices`: поиск (hostname / device_id / serial), теги, архив, пагинация (50), CSV export; на карточке — revoke/rotate key, архив, hard delete, подсказки дублей, inventory summary, копирование серийников / IP / MAC.
- **Время в UI:** локальный формат **ЧЧ:ММ:СС ДД.ММ.ГГГГ**; хранение в API/БД — UTC.
- **События** `/events`: лента изменений + пагинация.
- **Параметры** `/settings/*` — оболочка в духе «Параметры Windows 11» (левый список с иконками):
  - Доступ / LDAP (`allowed_group` = sAMAccountName группы AD)
  - Почта и уведомления (SMTP + чекбоксы событий; без webhooks)
  - Хранение и очистка (сроки хранения событий/снимков, порог **«устарел»** в минутах, фоновый prune)
  - Резервные копии (daily `pg_dump -Fc` + **Скачать site bundle**; restore `restore-site-bundle.sh`)
  - Политики агента (`update_target`: latest / pin)
  - **Обновление сервера** (`/settings/server-update`): ветка default `main`, check/apply/rollback ≤3 (branch+sha), token без plaintext; apply через systemd helper (не sudo-password); MSI `workflow_dispatch` отдельно от зеркала агента — [operator-guide](operator-guide.md#4-обновление-сервера-из-github)
  - Обновления агента (каталог MSI, «Подгрузить в зеркало», Latest; секция Enrollment + «Сменить enrollment token»)
- **Обзор**: empty mirror, version drift, broken pin, revoked active.
- Login: local first, optional LDAP; local admin — break-glass. Не возвращать paste-admin-token gate.
- Операторский runbook: [operator-guide.md](operator-guide.md).

## Агент

- Не добавлять UI в v1.
- Сбой одного collector не валит весь снимок.
- Atomic replace при записи `config.json`.
- Интервалы по умолчанию: inventory 6h, heartbeat 15m, update check 24h (могут быть переопределены remote config).
- Remote settings применяются только к safe knobs; `server_url` / secrets не трогать.
- Service CLI elevated: `BadAgent.exe service status|start|stop|restart` ([agents.md](agents.md)).
- Self-update: download → sha256 → msiexec → exit (файлы разблокируются для MajorUpgrade).

## Коммиты и PR

- Ветки по задаче; PR в `main` с ясным описанием «что / зачем».
- Не коммитить `.env`, `site.env`, локальные `*.db`, `bin/`/`obj/`, MSI build outputs.
- Менять locked-решения плана только осознанно и с обновлением docs.
- После изменения публичного контракта API — обновить тесты и `docs/architecture.md` (+ `agents.md` / `guideline.md` при update/CLI).

## Тесты

Unit tests (`agent/tests/`, `server/tests/`) — **только локально**, не коммитить в GitHub; CI их не гоняет.

- Локально (если деревья есть): сервер — `pytest -q`; агент — `dotnet test tests/BadAgent.Tests -c Release`.
- Покрывать: enroll → inventory → admin/web login + agent-update + policy/override; revoke/rotate, archive, retention, SMTP, backup; xUnit collector/schema, cleartext reject, semver/sha256, service CLI, ApplyRemoteSettings.
- Предпочитать узкие регрессии инвариантов (auth, schema, upsert, update compare, config precedence), а не хрупкие snapshot-гиганты.

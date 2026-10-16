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
- JSON, `Content-Type: application/json`, `Authorization: Bearer <token>`.
- Разделять enrollment token, agent API key и admin token.
- Ошибки: осмысленный HTTP status + краткий `detail`; неизвестный `schema_version` → `400`.
- Не включать OpenAPI UI в production (`docs_url=None` уже так).
- Новые поля в inventory — обратно совместимо внутри `schema_version=1` или новый integer schema с явной поддержкой на сервере.
- Update endpoints: agent key на `/v1/agent/update/*`; admin на `/v1/admin/agent-update*`.
- Remote config: agent key только на `GET /v1/agent/config` (и piggyback в heartbeat); мутации policies/overrides — admin session/token. Только allowlisted knobs, без shell/команд.

## Безопасность

- Агент отклоняет `http://` без явного opt-in для dev.
- На сервере: hash секретов (argon2), файл БД `0600`, site.env `640` root:bad; каталог бэкапов — как секреты (`700` / файлы `600`).
- **SEC-005:** `data_key` / `session_secret` по умолчанию в той же SQLite → копия БД или daily backup = полный компромисс SMTP/LDAP bind и session cookies. Вынос master key в `BAD_DATA_KEY` (файл вне БД, права `440`/`400` root:bad) — единственный способ разорвать эту связку; пока ключ в БД — не шарить бэкапы. Операторский чеклист: [operator-guide.md](operator-guide.md#безопасность-для-операторов).
- **SEC-011:** MSI write-config не кладёт token в argv PowerShell (HKLM Setup); residual — родительский `msiexec … ENROLLMENTTOKEN=` / verbose logs — не пересылать; после волны ротировать site enrollment token (UI в **0.10**, runbook: [operator-guide.md](operator-guide.md#ротация-enrollment-token-после-волны-msi)).
- **SEC-003:** LDAP TLS — по умолчанию `CERT_REQUIRED`; lab opt-in `tls_insecure` только для лаборатории, не для боя.
- После install **сразу** сменить `admin`/`admin` (`/account/password`); до смены UI пускает только `/account/password` и `/logout` (навигация скрыта).
- Cookie `bad_session`: после TLS — Secure + HTTPS; **0.11 bootstrap** — HTTP UI (`BAD_COOKIE_SECURE=0`), агентов на HTTP не ставить. TLS только nginx; UI **Параметры → Сертификат** (`/settings/tls`) → `/etc/bad/tls/*` + `bad-apply-tls`. ACME не обещать. Runbook: [operator-guide.md](operator-guide.md#сертификат-tls-из-панели-011).
- uvicorn не наружу.
- nginx rate-limit / app enroll limiter — сохранять и ужесточать осторожно.
- ProgramData ACL: Administrators + SYSTEM; не world-readable.
- Логи (Serilog / journald): без plaintext tokens и API keys (включая `BAD_GITHUB_TOKEN` и enrollment).

## Логирование

- Сервер: структурированно через стандартный logging / journalctl unit `bad-api`.
- Агент: Serilog file sink под `%ProgramData%\blazerity\bAD\logs\` (ротация ~7 дней); msiexec log рядом при upgrade.
- Сообщения — actionable (enroll failed, backoff, update sha mismatch), без секретов.

## Версионирование продукта

- Semver продукта: сейчас **`0.10.0`** (см. корневой `VERSION` и [agents.md](agents.md)).
- Правило bump: **patch +0.0.1** для hotfix; **minor +0.1.0** для feature; **major** только по явному решению владельца.
- `schema_version` протокола inventory — отдельный integer, не путать с semver агента/сервера.
- Агент шлёт `agent_version`; сервер отдаёт `version` в `/v1/health`.

## Как вырезать релиз агента (MSI)

1. Версия на `main` = нужному semver (сейчас **0.10.0**); checklist в [agents.md](agents.md).
2. Тег и push:
   ```bash
   git tag v0.10.0
   git push origin v0.10.0
   ```
3. Workflow **`release-msi`** (`windows-latest`): publish agent → WiX v5 → GitHub Release assets `bad-agent-<ver>.msi` + `agent-release.json`.
4. Права: `contents: write`. Для public repo достаточно `GITHUB_TOKEN`. Private позже — `BAD_GITHUB_TOKEN` на сервере.
5. На сервере: background sync или `POST /v1/admin/agent-update/sync`.
6. Агенты подтянут на check (старт / раз в сутки) или после `BadAgent.exe service restart`.

**Не обещать**: что MSI уже собирается в Linux CI — нет. Первый downloadable MSI появляется после успешного Windows GHA (или локальной Windows-сборки).

Ручной запуск: Actions → `release-msi` → `workflow_dispatch`.

## Зеркало на сервере

В `/etc/bad/site.env`:

```bash
BAD_GITHUB_REPO=blazerity/bAD
BAD_AGENT_UPDATES_DIR=/var/lib/bad/agent-updates
BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS=3600
BAD_AGENT_UPDATE_SYNC_ON_STARTUP=true
# BAD_GITHUB_TOKEN=...   # только если repo private
BAD_BACKUP_DIR=/var/lib/bad/backups
# BAD_BACKUP_INTERVAL_SECONDS=3600
```

## Web UI (admin)

Единый раздел (с **0.8.0**). Не плодить противоречащие описания «без дашборда» — обзорная сводка есть, marketing landing нет.

- **Язык / look**: Windows 11 / Fluent light, русский UI; `static/style.css`, favicon; stroke-иконки секций; HTML-отчёт CLI в той же семье токенов.
- **Обзор** `/` (`/overview`): totals (активные / онлайн / устарели / архив), breakdown версий агента, последние события железа.
- **Устройства** `/devices`: поиск (hostname / device_id / serial), теги, архив, пагинация (50), CSV export; на карточке — revoke/rotate key, архив, hard delete, подсказки дублей, inventory summary.
- **События** `/events`: лента изменений + пагинация.
- **Параметры** `/settings/*` — оболочка в духе «Параметры Windows 11» (левый список с иконками):
  - Доступ / LDAP (`allowed_group` = sAMAccountName группы AD)
  - Почта и уведомления (SMTP + чекбоксы событий; без webhooks)
  - Хранение и очистка (retention days + фоновый prune)
  - Резервные копии (daily SQLite + **Скачать site bundle**; restore `restore-site-bundle.sh`)
  - Политики агента (`update_target`: latest / pin)
  - Обновления агента (каталог MSI, «Подгрузить в зеркало», Latest; секция Enrollment + «Сменить enrollment token»)
- **Обзор** (0.10): empty mirror, version drift, broken pin, revoked active.
- Login: local first, optional LDAP; local admin — break-glass. Не возвращать paste-admin-token gate.
- Операторский runbook 0.10: [operator-guide.md](operator-guide.md).

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
- Покрывать: enroll → inventory → admin/web login + agent-update + policy/override; сервис 0.8.0 (revoke/rotate, archive, retention, SMTP, backup); xUnit collector/schema, cleartext reject, semver/sha256, service CLI, ApplyRemoteSettings.
- Предпочитать узкие регрессии инвариантов (auth, schema, upsert, update compare, config precedence), а не хрупкие snapshot-гиганты.

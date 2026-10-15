# Руководства по разработке bAD

Краткие инженерные правила для этого репозитория. Стек и границы v1 зафиксированы в [architecture-plan.md](architecture-plan.md).

## Общие принципы

- **Thin agent**: агент только собирает и POST’ит; бизнес-логика и хранение — на сервере.
- **Idempotent upsert**: стабильный `device_id`; повторная отправка безопасна.
- **Least privilege / secrets**: TLS везде; секреты не вшивать в MSI binary; не логировать tokens/API keys/пароли.
- **MVP scope**: не раздувать web UI, плагины, cloud control plane; LDAP — optional и настраивается из UI.

## API

- Префикс версионирования пути: `/v1/...`.
- JSON, `Content-Type: application/json`, `Authorization: Bearer <token>`.
- Разделять enrollment token, agent API key, admin API token и web-аккаунты.
- Admin API (`/v1/devices*`) — **только Bearer admin token**; session cookie браузера туда не подходит.
- Ошибки: осмысленный HTTP status + краткий `detail`; неизвестный `schema_version` → `400`.
- Не включать OpenAPI UI в production (`docs_url=None` уже так).
- Новые поля в inventory — обратно совместимо внутри `schema_version=1` или новый integer schema с явной поддержкой на сервере.

## Безопасность

- Агент отклоняет `http://` без явного opt-in для dev.
- На сервере: hash секретов и паролей (argon2), файл БД `0600`, site.env `640` root:bad.
- LDAP bind password — Fernet (`site_secrets.data_key`); никогда не отдавать plaintext обратно в HTML-форму (placeholder «unchanged»).
- Дефолт `admin`/`admin` только при отсутствии local users; форсировать/подталкивать смену пароля.
- nginx rate-limit / app enroll limiter — сохранять и ужесточать осторожно.
- ProgramData ACL: Administrators + SYSTEM; не world-readable.
- Логи (Serilog / journald): без plaintext tokens, API keys и паролей.

## Логирование

- Сервер: структурированно через стандартный logging / journalctl unit `bad-api`.
- Агент: Serilog file sink под `%ProgramData%\blazerity\bAD\logs\` (ротация ~7 дней).
- Сообщения — actionable (enroll failed, backoff, collector section null), без секретов.

## Версионирование продукта

- Semver продукта: сейчас **`0.2.0`** (см. корневой `VERSION` и [agents.md](agents.md)).
- Правила владельца: patch `+0.0.1` hotfix; minor `+0.1.0` feature; major — только по явному указанию.
- Один minor bump на feature-set, попадающий в `main`; не двойной bump, если соседний PR уже поднял ту же minor.
- `schema_version` протокола inventory — отдельный integer, не путать с semver агента/сервера.
- Агент шлёт `agent_version`; сервер отдаёт `version` в `/v1/health`.

## Web UI

- Задачи: просмотр парка/inventory + login + LDAP settings (admin).
- Login: username/password (local first, optional LDAP). Не возвращать paste-admin-token gate.
- Без редактирования активов, графиков, «дашборд-шума».
- Сохранять существующий визуальный язык (`static/style.css`).

## Агент

- Не добавлять UI в v1.
- Сбой одного collector не валит весь снимок.
- Atomic replace при записи `config.json`.
- Интервалы по умолчанию: inventory 6h, heartbeat 15m (конфиг может переопределить).

## Коммиты и PR

- Ветки по задаче; PR в `main` с ясным описанием «что / зачем».
- Не коммитить `.env`, `site.env`, локальные `*.db`, `bin/`/`obj/`, MSI build outputs.
- Менять locked-решения плана только осознанно и с обновлением docs.
- После изменения публичного контракта API или auth — обновить тесты и `docs/architecture.md` / `docs/guideline.md` / `docs/agents.md`.

## Тесты

- Сервер: pytest — enroll → inventory → admin get; local login success/fail; LDAP settings CRUD с mock ldap3; devices требуют session.
- Агент: xUnit на collector/schema и отказ от cleartext HTTP.
- Предпочитать узкие регрессии инвариантов (auth, schema, upsert), а не хрупкие snapshot-гиганты.

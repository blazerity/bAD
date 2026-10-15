# Руководства по разработке bAD

Краткие инженерные правила для этого репозитория. Стек и границы v1 зафиксированы в [architecture-plan.md](architecture-plan.md).

## Общие принципы

- **Thin agent**: агент только собирает и POST’ит; бизнес-логика и хранение — на сервере.
- **Idempotent upsert**: стабильный `device_id`; повторная отправка безопасна.
- **Least privilege / secrets**: TLS везде; секреты не вшивать в MSI binary; не логировать tokens/API keys.
- **MVP scope**: не раздувать web UI, роли, плагины, cloud control plane.

## API

- Префикс версионирования пути: `/v1/...`.
- JSON, `Content-Type: application/json`, `Authorization: Bearer <token>`.
- Разделять enrollment token, agent API key и admin token.
- Ошибки: осмысленный HTTP status + краткий `detail`; неизвестный `schema_version` → `400`.
- Не включать OpenAPI UI в production (`docs_url=None` уже так).
- Новые поля в inventory — обратно совместимо внутри `schema_version=1` или новый integer schema с явной поддержкой на сервере.

## Безопасность

- Агент отклоняет `http://` без явного opt-in для dev.
- На сервере: hash секретов (argon2), файл БД `0600`, site.env `640` root:bad.
- nginx rate-limit / app enroll limiter — сохранять и ужесточать осторожно.
- ProgramData ACL: Administrators + SYSTEM; не world-readable.
- Логи (Serilog / journald): без plaintext tokens и API keys.

## Логирование

- Сервер: структурированно через стандартный logging / journalctl unit `bad-api`.
- Агент: Serilog file sink под `%ProgramData%\blazerity\bAD\logs\` (ротация ~7 дней).
- Сообщения — actionable (enroll failed, backoff, collector section null), без секретов.

## Версионирование продукта

- Semver продукта: сейчас **`0.1.0`** (см. корневой `VERSION` и [agents.md](agents.md)).
- `schema_version` протокола inventory — отдельный integer, не путать с semver агента/сервера.
- Агент шлёт `agent_version`; сервер отдаёт `version` в `/v1/health`.

## Web UI (admin, read-only)

- Одна задача: просмотр парка и последнего inventory.
- Без редактирования активов, графиков, ролей, «дашборд-шума».
- Простой login по admin token; остальное — список + деталь.
- Сохранять существующий визуальный язык (`static/style.css`), не превращать в marketing landing.

## Агент

- Не добавлять UI в v1.
- Сбой одного collector не валит весь снимок.
- Atomic replace при записи `config.json`.
- Интервалы по умолчанию: inventory 6h, heartbeat 15m (конфиг может переопределить).

## Коммиты и PR

- Ветки по задаче; PR в `main` с ясным описанием «что / зачем».
- Не коммитить `.env`, `site.env`, локальные `*.db`, `bin/`/`obj/`, MSI build outputs.
- Менять locked-решения плана только осознанно и с обновлением docs.
- После изменения публичного контракта API — обновить тесты и `docs/architecture.md`.

## Тесты

- Сервер: pytest вокруг enroll → inventory → admin get + web login path.
- Агент: xUnit на collector/schema и отказ от cleartext HTTP.
- Предпочитать узкие регрессии инвариантов (auth, schema, upsert), а не хрупкие snapshot-гиганты.

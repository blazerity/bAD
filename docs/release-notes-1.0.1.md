# bAD 1.0.1

Hotfix после 1.0.0.

## Изменения

- Удалены неиспользуемые `server/bad_server/migrations/*.sql` (схема по-прежнему в `db.py`).
- Сжата semver-археология `0.x` в канонических docs.
- Мобильная адаптивность web-панели (из 1.0.0+ #55, входит в линию main).

`schema_version` inventory без изменений. API `/v1` — additive freeze.

# bAD 1.0.0

Первый major-релиз по решению владельца. База: on-prem Windows-агент + панель после тем A+B+C (~0.12).

## Что вошло

- **A — HTTPS и секреты:** агент/CLI HTTPS-first; security-status; хук ротации enrollment после волны MSI.
- **B — операторский парк:** чеклист первого запуска, лента «требует действие», победитель конфига, фильтры волны.
- **C — политики и API:** allowlist knobs; стабильный additive `/v1` для интеграций (**1C Itilium** и др.) — см. [api-v1.md](api-v1.md).

`schema_version` inventory не менялся (остаётся integer 1|2).

## Артефакты

- Сервер / Debian: `VERSION` = `1.0.0`
- MSI: `bad-agent-1.0.0.msi` (GitHub Release `v1.0.0`)

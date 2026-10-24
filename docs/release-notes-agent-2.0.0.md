# Релизные заметки — агент 2.0.0 (MSI)

Мажорная линия установщика и службы. **Данные на ПК не переезжают:** `%ProgramData%\blazerity\bAD\` (config, очередь, логи) — тот же путь.

## Установка на диск

- Каталог: **`%ProgramFiles%\blazerity\bad agent\`** (`bin\`, `scripts\`, `bad.cmd`).
- Служба Windows: короткое имя **`badagent`**, в оснастке «Службы» — **bAD Agent**, описание на русском («собирает сведения об оборудовании и ОС и отправляет их на сервер bAD»).

## Апгрейд с 1.x

- Установка MSI **2.0.0** поверх **1.x** — штатный **MajorUpgrade** (тот же код продукта WiX).
- Перед запуском новой службы выполняется **`migrate-legacy-install.ps1`**: останавливается старая служба **`BlazerityAssetDiscovery`**, убирается каталог **`%ProgramFiles%\blazerity\bAD\`**, чистятся устаревшие записи в PATH.
- Self-update с сервера и откат версии (pin) используют тот же механизм.

## CLI

- Канон: **`bad`**, **`bad -r`**, **`bad -c`**, **`bad config`**, **`bad push`**, **`bad update`**, **`bad service status|start|stop|restart`** (от администратора).
- Справка: **`bad -h`**. Старые синонимы вроде `report` / `info` в коде могут ещё приниматься, в документации не используются.

Предыдущая линия: [release-notes-agent-1.3.1.md](release-notes-agent-1.3.1.md).

# Релизные заметки — сервер 2.3.5

Мелкая уборка после UI 2.3.4.

## Устройства

- Фильтры: снова подсветка активных селектов (стили отвязаны от удалённого `.devices-catalog-filters`).
- CPU в списке: `format_cpu_short` без двойного `i` (`ii5…` → `i5…`), поколение с любой стороны строки.

## Прочее

- CSS: убраны мёртвые блоки toolbar-refactor, дубль `digest-schedule-preview`, лишний `main:has(.overview-admin)`.
- Graphify: отмечены модули web UI layout (toolbar, formatters, event feed, SMTP digest).

Предыдущий релиз: [release-notes-2.3.4.md](release-notes-2.3.4.md).

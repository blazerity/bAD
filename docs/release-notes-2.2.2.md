# Релизные заметки — сервер 2.2.2

Хотфикс дашборда. Агент без изменений (**2.0.2**).

## Исправление

- 500 на `/dashboard`: в макросе `rank_bars` обращение `block.items` в Jinja брало метод `dict.items`, а не список строк. Заменено на `block['items']` / `block['others_full']`.

Предыдущий релиз: [release-notes-2.2.1.md](release-notes-2.2.1.md).

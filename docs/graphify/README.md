# Граф кода bAD (Graphify)

Собран через [Graphify](https://github.com/Graphify-Labs/graphify) (`graphify extract . --code-only`).

| Файл | Назначение |
|------|------------|
| `graph.html` | Интерактивный граф в браузере |
| `GRAPH_REPORT.md` | Обзор сообществ и ключевых узлов |
| `graph.json` | Полный граф для `graphify query` / `path` / `explain` |

Пересборка (без LLM):

```bash
graphify extract . --code-only
# или обновление кода:
graphify update .
cp -a graphify-out/. docs/graphify/
```

Агентам: сначала спрашивать этот граф, потом читать исходники — так меньше токенов.

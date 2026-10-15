# Граф кода bAD (Graphify)

Собран через [Graphify](https://github.com/Graphify-Labs/graphify): `graphify extract . --code-only` + `graphify cluster-only . --no-label`.

| Файл | Назначение |
|------|------------|
| [graph.html](graph.html) | Интерактивный граф |
| [GRAPH_REPORT.md](GRAPH_REPORT.md) | Обзор сообществ и ключевых узлов |
| [graph.json](graph.json) | Полный граф для `graphify query` / `path` / `explain` |

Пересборка без LLM:

```bash
graphify extract . --code-only
graphify cluster-only . --no-label
rm -rf docs/graphify && mkdir -p docs/graphify
cp graphify-out/graph.json graphify-out/GRAPH_REPORT.md graphify-out/graph.html docs/graphify/
```

Агентам: сначала граф, потом точечное чтение исходников.

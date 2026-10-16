# bAD Agent

Windows Worker Service (.NET 8) для инвентаризации: enroll / heartbeat / inventory / self-update через серверное зеркало MSI.

HTTP bootstrap панели ≠ HTTP у агента: в бою `server_url` только `https://`. Reject cleartext без lab opt-in (`BAD_ALLOW_HTTP=1` — точное значение, только lab). Правила общие для службы и `bad config` (`ServerUrlRules`).

Локальный CLI: `bad -c` — интерактивная настройка; `bad -r` — HTML; `bad -h` — справка; `bad config` — просмотр без секретов.
Ручные knobs: `MarkAgentLocalKey` / `MarkServerUrlLocal` → `agent_local_keys` / `server_url_local`; heartbeat `config_local`.

## Сборка

```bash
cd agent
dotnet build BadAgent.sln -c Release
```

Локальные unit tests (gitignored, не в GitHub): `tests/BadAgent.Tests` — `dotnet test tests/BadAgent.Tests -c Release`.

Подробности: [docs/agents.md](../docs/agents.md), установка MSI: [installer/msi/](../installer/msi/).

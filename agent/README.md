# bAD Agent

Windows Worker Service (.NET 8) для инвентаризации: enroll / heartbeat / inventory / self-update через серверное зеркало MSI.

HTTP bootstrap панели на сервере ≠ поддержка HTTP у агента: агент по умолчанию принимает только `https://` (`BAD_ALLOW_HTTP=1` — только lab).

## Сборка

```bash
cd agent
dotnet build BadAgent.sln -c Release
```

Локальные unit tests (gitignored, не в GitHub): `tests/BadAgent.Tests` — `dotnet test tests/BadAgent.Tests -c Release`.

Подробности: [docs/agents.md](../docs/agents.md), установка MSI: [installer/msi/](../installer/msi/).

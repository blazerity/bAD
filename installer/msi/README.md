# MSI агента

Сборка только на Windows (WiX v5). Тег `agent-v*` публикует `bad-agent-<версия>.msi`. Тег `server-v*` MSI не собирает. Версия берётся из `agent/VERSION`.

На ПК агент ставится так, как написано в [docs/ste-100.md](../../docs/ste-100.md): свойство `SERVERURL=https://<домен>`, без `ENROLLMENTTOKEN`, если ПК идёт заявкой.

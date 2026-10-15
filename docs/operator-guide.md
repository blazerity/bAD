# Операторский гайд — bAD

Путь end-to-end: установить сервер → поставить Windows MSI агента → увидеть устройство в web UI.

## 1. Сервер (Debian 12)

Подготовьте TLS-сертификат и ключ, у которых CN/SAN совпадает с публичным DNS-именем.

```bash
# Из release-тарбола или git checkout с deploy/debian + server/
BAD_DOMAIN=bad.example.com \
BAD_TLS_CERT=/etc/ssl/certs/bad.fullchain.pem \
BAD_TLS_KEY=/etc/ssl/private/bad.privkey.pem \
  sudo -E bash deploy/debian/install.sh
```

Скрипт один раз печатает:

- `https://bad.example.com/`
- enrollment token (для MSI агента)
- admin API token (Bearer для автоматизации)

Проверка:

```bash
curl -fsS https://bad.example.com/v1/health
# → {"status":"ok","version":"0.9.1"}
```

### Вход в web (локальный)

1. Откройте `https://bad.example.com/login`
2. Войдите локальным аккаунтом по умолчанию: **`admin` / `admin`**
3. Сразу смените пароль (`Пароль` в шапке или принудительный редирект)

Работает **без настроенного LDAP**. Admin API token для браузерного UI **не** используется.

Токены лежат в `/etc/bad/site.env` (режим `640`, `root:bad`). uvicorn слушает только `127.0.0.1:8000`; nginx терминирует TLS на 443.

### Опционально: LDAP из UI

1. Войдите как локальный **admin**
2. Откройте **LDAP** (`/settings/ldap`)
3. Заполните host, port, SSL/StartTLS, bind DN + bind password, user search base, filter template (должен содержать `{username}`), атрибут display name, роль по умолчанию
4. **Сохранить**, затем **Проверить подключение**
5. Включите вход по LDAP; пользователи каталога смогут входить на `/login` (сначала пробуются локальные)

Bind password хранится в SQLite зашифрованным и после save больше не показывается (оставьте поле пустым, чтобы не менять).

Важно: смените пароль `admin`/`admin` до публикации UI за пределы доверенной сети.

## 2. Windows-агент (MSI)

На Windows build-хосте соберите MSI (см. `installer/msi/README.md`), затем установите:

```powershell
msiexec /i bad-agent-0.9.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  /qn
```

Опциональный PATH для локального CLI `bad` (по умолчанию выкл.):

```powershell
msiexec /i bad-agent-0.9.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  ADDPATH=1 `
  /qn
```

Служба `BlazerityAssetDiscovery` стартует автоматически, один раз enroll'ится, сохраняет API key в `%ProgramData%\blazerity\bAD\config.json` и шлёт inventory при старте (далее каждые 6 часов), heartbeat каждые 15 минут. Также спрашивает сервер про MSI-обновления (никогда не GitHub напрямую). Локальный CLI (сервер не нужен): `bad` / `bad -h` / `bad -?`. Service CLI: `BadAgent.exe service status|start|stop|restart` (elevated). См. [agents.md](./agents.md).

## 3. Проверка в web UI

1. Откройте `https://bad.example.com/devices` (после входа)
2. Найдите hostname (badge здоровья: **OK**, если last seen в пределах stale-порога, иначе **stale**)
3. Откройте карточку устройства: теги, недавние события изменений, последний inventory JSON
4. Опционально: **События** (`/events`) — лог изменений по всем устройствам (новее сверху)

Теги: правка на странице устройства (через запятую). Фильтр списка устройств по тегу. Политики тоже могут матчить `tag equals/contains`.

Master-ключи (`/etc/bad/data_key`, `/etc/bad/session_secret`) не входят в daily SQLite backup — храните escrow отдельно. Порог stale по умолчанию 1 час (`BAD_DEVICE_STALE_AFTER_SECONDS`); поставьте ≈2× heartbeat, если удобнее (напр. `1800` при heartbeat 15 мин). Версия продукта **0.9.1**.

Альтернатива (автоматизация — admin API token):

```bash
curl -fsS -H "Authorization: Bearer <admin-token>" \
  https://bad.example.com/v1/devices
curl -fsS -H "Authorization: Bearer <admin-token>" \
  'https://bad.example.com/v1/events?limit=50'
```

## Заметки

- Апгрейд MSI сохраняет ProgramData (API key); повторный enroll не нужен.
- Не кладите enrollment или admin tokens в world-readable файлы.
- Локальные демо без TLS: uvicorn на Linux (`server/README.md`) и тестовый агент с `BAD_ALLOW_HTTP=1` на `http://127.0.0.1:8000`.

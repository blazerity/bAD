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
3. **Сразу смените пароль** (`Пароль` в шапке / `/account/password`). До смены сервер пускает только `/account/password` и `/logout` (навигация скрыта). Не публикуйте UI за пределы доверенной сети, пока пароль не сменён.

Работает **без настроенного LDAP**. Admin API token для браузерного UI **не** используется.

Токены лежат в `/etc/bad/site.env` (режим `640`, `root:bad`). uvicorn слушает только `127.0.0.1:8000`; nginx терминирует TLS на 443 (в проде обязателен HTTPS — cookie сессии рассчитан на TLS; см. [Безопасность](#безопасность-для-операторов)).

### Опционально: LDAP из UI

1. Войдите как локальный **admin**
2. Откройте **LDAP** (`/settings/ldap`)
3. Заполните host, port, SSL/StartTLS, bind DN + bind password, user search base, filter template (должен содержать `{username}`), атрибут display name, роль по умолчанию
4. **Сохранить**, затем **Проверить подключение**
5. Включите вход по LDAP; пользователи каталога смогут входить на `/login` (сначала пробуются локальные)

Bind password хранится в SQLite зашифрованным и после save больше не показывается (оставьте поле пустым, чтобы не менять).

**TLS к LDAP (SEC-003):** по умолчанию LDAPS/StartTLS с `CERT_REQUIRED` (system CA или свой). Lab opt-in: флаг `tls_insecure` в настройках LDAP — только для лаборатории, не для боевого AD через недоверенную сеть.

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

**Enrollment token (SEC-011):** deferred custom action читает token из HKLM `SOFTWARE\blazerity\bAD\Setup` и сразу удаляет ключ — **не** из argv PowerShell. Residual risk: родительский `msiexec … ENROLLMENTTOKEN=` (process command line) и verbose/`msiexec` логи / transcript’ы деплоя. Не пересылайте их. После волны установки **ротируйте** site enrollment token в `/etc/bad/site.env` (и перезапустите `bad-api`). Property `Hidden=yes` снижает утечку в UI MSI, но не убирает exposure в командной строке родителя. Подробнее: `installer/msi/README.md`.

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

## Безопасность для операторов

Краткий чеклист (детали — [guideline.md](guideline.md), [architecture.md](architecture.md)).

### БД и бэкапы = секреты сайта (SEC-005)

Fernet-ключ `data_key` (расшифровка SMTP/LDAP bind) и `session_secret` (подделка cookie `bad_session`) по умолчанию лежат **в той же SQLite**, что и `*_password_enc`. Поэтому:

- копия `/var/lib/bad/bad.db` или daily backup `bad-YYYY-MM-DD.db` = **полный компромисс** секретов сайта (не «просто inventory»);
- шифрование полей в БД **не** защищает at-rest при краже файла, пока master key рядом в той же БД.

**Права сейчас (минимум):**

```bash
# БД и WAL — только владелец bad
chown bad:bad /var/lib/bad/bad.db /var/lib/bad/bad.db-* 2>/dev/null || true
chmod 600 /var/lib/bad/bad.db

# Каталог бэкапов — не world-readable; файлы бэкапа как секреты
chown -R bad:bad /var/lib/bad/backups
chmod 700 /var/lib/bad/backups
chmod 600 /var/lib/bad/backups/bad-*.db
```

Не кладите бэкапы БД в общие шары/тикеты без отдельного контроля доступа. Не бэкапьте master key **вместе** с копией БД без раздельного key escrow.

**Вынести ключ из БД (`BAD_DATA_KEY`):** единственный способ, при котором кража *только* файла БД не даёт расшифровку SMTP/LDAP и подделку сессий — держать master key **вне** SQLite (env или файл). Пока ключ в `site_secrets`, считайте БД и бэкапы равносильными компромиссу. Когда ключ вынесен в файл:

```bash
# пример: отдельный файл ключа (не рядом с бэкапами без изоляции)
install -d -o root -g bad -m 750 /etc/bad/keys
# содержимое — url-safe Fernet key; читать может только сервис
install -o root -g bad -m 440 /path/from/secure/source /etc/bad/keys/data.key
# в site.env: BAD_DATA_KEY=/etc/bad/keys/data.key
# (или сам ключ в env — хуже для ps/audit)
```

Файл ключа: **не** 644/666; типично `440` или `400`, владелец `root:bad`. Не коммитьте ключ в git и не кладите в тот же tar, что и `bad.db`, без отдельного сейфа.

### Cookie и TLS

Штатный путь — только HTTPS через nginx (HSTS, redirect с 80). Не открывайте uvicorn наружу. Cookie `bad_session` должен уходить только по TLS (`Secure` за reverse-proxy / в prod); cleartext к приложению = риск перехвата сессии.

### Enrollment token (SEC-011)

См. выше в § MSI: не шарьте msiexec-логи; после массового деплоя ротируйте enrollment token.

## Заметки

- Апгрейд MSI сохраняет ProgramData (API key); повторный enroll не нужен.
- Не кладите enrollment или admin tokens в world-readable файлы.
- Локальные демо без TLS: uvicorn на Linux (`server/README.md`) и тестовый агент с `BAD_ALLOW_HTTP=1` на `http://127.0.0.1:8000` — только lab.

# Операторский гайд — bAD

Путь end-to-end: установить сервер → поставить Windows MSI агента → увидеть устройство в web UI.

## 1. Сервер (Debian 12)

Два пути (**0.11.0**): сразу с TLS-файлами при install **или** bootstrap по HTTP и загрузка cert из панели.

### Install сразу с TLS

Подготовьте сертификат и ключ, у которых CN/SAN совпадает с публичным DNS (`BAD_DOMAIN`).

```bash
# Из release-тарбола или git checkout с deploy/debian + server/
BAD_DOMAIN=bad.example.com \
BAD_TLS_CERT=/etc/ssl/certs/bad.fullchain.pem \
BAD_TLS_KEY=/etc/ssl/private/bad.privkey.pem \
  sudo -E bash deploy/debian/install.sh
```

Скрипт один раз печатает URL (`https://…`), enrollment token и admin API token. Дальше — [вход](#вход-в-web-локальный) по HTTPS.

### Install без cert (HTTP bootstrap → upload в UI)

С **0.11.0** `BAD_TLS_CERT` / `BAD_TLS_KEY` **опциональны**. Без них nginx поднимается в HTTP-only (:80), без HSTS и без 301 на HTTPS, пока не появится managed cert.

```bash
BAD_DOMAIN=bad.example.com \
  sudo -E bash deploy/debian/install.sh
# → UI: http://bad.example.com/  (пока нет сертификата)
```

Краткий порядок (детали — [чеклист окна HTTP bootstrap](#чеклист-окна-http-bootstrap-011)):

1. Откройте **`http://bad.example.com/login`** (не https) **только** из доверенного контура.
2. Войдите `admin` / `admin`, **сразу смените пароль**.
3. Загрузите cert+key: [§ Сертификат из панели](#сертификат-tls-из-панели-011).
4. После успешного apply — **`https://…`**, **обязательный повторный вход** (non-Secure cookies на HTTPS не уходят).
5. **Агентов (MSI) ставьте только после HTTPS** — bootstrap HTTP для агентов не предназначен (`BAD_ALLOW_HTTP` — только lab).

#### Чеклист окна HTTP bootstrap (0.11)

Временный режим UI до managed cert. **Risk rating: Medium** при соблюдении runbook (доверенная сеть + короткое окно); на публичном `:80` до cert — **High**.

| # | Действие | Статус |
|---|----------|--------|
| 1 | Доступ к `:80` **только** из доверенного контура (LAN / VPN / `ssh -L`). **Не** публиковать панель в интернет до cert. | ☐ |
| 2 | Войти `admin` / `admin` → **сразу** сменить пароль (`/account/password`). | ☐ |
| 3 | Загрузить cert+key на **Параметры → Сертификат** → «Установить и перезагрузить nginx». | ☐ |
| 4 | Открыть **`https://…`**, **войти заново** (старые non-Secure cookies на HTTPS не уходят). | ☐ |
| 5 | **Не** ставить MSI / агентов, пока режим «HTTP bootstrap». Только после «HTTPS активен». | ☐ |
| 6 | **Не** по HTTP: скачивание site-bundle, сохранение LDAP/SMTP с боевыми паролями, ротация enrollment «впрок», массовый enroll. | ☐ |
| 7 | Если cert уже есть на диске — install сразу с `BAD_TLS_CERT`/`BAD_TLS_KEY`, без HTTP-окна. | ☐ |

После волны MSI — [ротация enrollment](#ротация-enrollment-token-после-волны-msi) (SEC-011).

Проверка health:

```bash
curl -fsS http://bad.example.com/v1/health   # bootstrap без cert
curl -fsS https://bad.example.com/v1/health  # после TLS / с cert при install
# → {"status":"ok","version":"0.11.0"}
```

### Вход в web (локальный)

1. Откройте URL из вывода install (`http://…/login` при bootstrap или `https://…/login`).
2. Войдите локальным аккаунтом по умолчанию: **`admin` / `admin`**
3. **Сразу смените пароль** (`Пароль` в шапке / `/account/password`). До смены сервер пускает только `/account/password` и `/logout` (навигация скрыта). Не публикуйте UI за пределы доверенной сети, пока пароль не сменён.

Работает **без настроенного LDAP**. Admin API token для браузерного UI **не** используется.

Токены лежат в `/etc/bad/site.env` (режим `640`, `root:bad`). uvicorn — только `127.0.0.1:8000`; TLS терминирует **nginx** (не uvicorn). См. [Безопасность](#безопасность-для-операторов).

### Сертификат TLS из панели (0.11)

Страница: **Параметры → Сертификат** (`/settings/tls`, nav desc «TLS для nginx») — только web admin. Заголовок **«Сертификат TLS»**.

На странице видно:

- **Режим:** «HTTP bootstrap» или «HTTPS активен»
- **Домен (BAD_DOMAIN)** — read-only
- пути **fullchain** / **privkey на диске:** да|нет (plaintext key **не** показывается)
- при установленном cert — Subject / Issuer / Not after / SAN / fingerprint; **Последний apply**

**Куда кладётся на диске**

| Файл | Путь |
|------|------|
| Fullchain (leaf [+ intermediates]) | `/etc/bad/tls/fullchain.pem` |
| Private key | `/etc/bad/tls/privkey.pem` |
| Staging (до apply) | `/etc/bad/tls/staging/` |

**Загрузить / заменить (ротация)**

1. Admin → **Параметры → Сертификат** (`/settings/tls`).
2. Секция **«Загрузить сертификат и ключ»**: поля **«Сертификат (PEM)»**, **«Private key (PEM)»**, опционально **«Цепочка / intermediates»**.
3. **«Установить и перезагрузить nginx»** (`POST /settings/tls`, CSRF). Validate → staging → helper `bad-apply-tls` (`nginx -t` + reload через `bad-tls-apply.path`). uvicorn TLS не держит.
4. При ошибке (bad PEM / key mismatch / `nginx -t`) боевые файлы не меняются — сообщение в UI.
5. После успеха: режим **«HTTPS активен»**, :80→301, HSTS; cookie Secure сразу по `X-Forwarded-Proto` (`BAD_COOKIE_SECURE=auto`). Откройте **HTTPS**, войдите снова.
6. Повторная загрузка тех же полей = ротация cert (тот же flow).

Ручной retry apply: `systemctl start bad-tls-apply.service` (логи: `journalctl -u bad-tls-apply`). Let’s Encrypt / ACME в 0.11 нет. Смена `BAD_DOMAIN` из UI — вне scope.

**Что не делать с ключом**

- Не вшивать в MSI, не коммитить, не класть в world-readable каталоги / общие шары.
- Не пересылать `privkey.pem` в тикет «для проверки» — в UI достаточно **«privkey на диске: да»**.
- Не править `/etc/bad/tls/*` вручную параллельно с upload (гонка со staging/apply).
- Не оставлять операторов и агентов на HTTP после появления cert.

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
msiexec /i bad-agent-0.10.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  /qn
```

Опциональный PATH для локального CLI `bad` (по умолчанию выкл.):

```powershell
msiexec /i bad-agent-0.10.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  ADDPATH=1 `
  /qn
```

**Enrollment token (SEC-011):** deferred custom action читает token из HKLM `SOFTWARE\blazerity\bAD\Setup` и сразу удаляет ключ — **не** из argv PowerShell. Residual risk: родительский `msiexec … ENROLLMENTTOKEN=` (process command line) и verbose/`msiexec` логи / transcript’ы деплоя. Не пересылайте их. После волны установки **ротируйте** enrollment token (runbook ниже). Property `Hidden=yes` снижает утечку в UI MSI, но не убирает exposure в командной строке родителя. Подробнее: `installer/msi/README.md`.

**Если установка падает до появления логов агента** (пустой `%ProgramData%\blazerity\bAD\logs`, диалог MSI 1722): смотрите `%ProgramData%\blazerity\bAD\logs\msi-install.log` / `msi-ca-error.txt` (коды `BAD_MSI_###`) и `%TEMP%\MSI*.log`. Подробности: `installer/msi/README.md` → «Логи установки».

Служба `BlazerityAssetDiscovery` стартует автоматически, один раз enroll'ится, сохраняет API key в `%ProgramData%\blazerity\bAD\config.json` и шлёт inventory при старте (далее каждые 6 часов), heartbeat каждые 15 минут. Также спрашивает сервер про MSI-обновления (никогда не GitHub напрямую). Локальный CLI (сервер не нужен): `bad` / `bad -r` (HTML) / `bad -c` (настройка) / `bad -h` (справка). На карточке устройства метка **«задано на агенте»** = knobs с машины (`agent_local`), не политика и не server override. Service CLI: `BadAgent.exe service status|start|stop|restart` (elevated). См. [agents.md](./agents.md).

### Ротация enrollment token (после волны MSI)

**Зачем.** Site enrollment token — общий секрет для первой регистрации агентов. Он может остаться в логах `msiexec`, transcript’ах деплоя или истории команд. Пока токен жив, им можно enroll’ить (и при известных рисках пытаться злоупотреблять enroll). Ротация инвалидирует **старый** токен для новых установок.

**Когда.** Сразу после волны массовой установки MSI (или если токен мог утечь: логи ушли в тикет, скрипт деплоя в общем репо, и т.п.). Уже зарегистрированные устройства **не** нужно переустанавливать: у них в ProgramData лежит API key, enrollment token им больше не нужен.

**Шаги (UI, 0.10):**

1. Войдите как локальный **admin** (или LDAP admin).
2. Откройте **Параметры → Обновления агента** (`/settings/updates`) — внизу секция **Enrollment token** (plaintext текущего token не показывается; видны «Hash в БД» / путь файла).
3. При желании введите свой токен в поле «Свой токен» (пусто = сервер сгенерирует).
4. Нажмите **Сменить enrollment token**, подтвердите диалог («Старый перестанет работать»).
5. На той же странице появится блок **«Новый enrollment token (показать один раз)»** — скопируйте в сейф. Restart `bad-api` **не** нужен (hash в SQLite сразу). Повторно plaintext не откроется.
6. Обновите артефакты деплоя: в следующих `msiexec` / GPO / Intune — новый `ENROLLMENTTOKEN=…`.

Автоматизация: `POST /v1/admin/enrollment/rotate` (admin Bearer) — тот же эффект; plaintext нового token в ответе один раз. Endpoint формы: `POST /settings/enrollment/rotate` (CSRF).

**Что со старым токеном.** После ротации `POST /v1/enroll` со старым Bearer → отказ (401). Уже enroll’енные агенты продолжают heartbeat/inventory по своему API key. Revoke/rotate **API key** устройства — отдельная операция на карточке устройства, не путать с ротацией site enrollment.

**Новые установки.** Только с новым token. Если машина ещё не успела enroll’иться со старым — поставьте MSI заново с новым `ENROLLMENTTOKEN`.

**Fallback без UI (аварийно):** сгенерировать новый секрет → `/etc/bad/site.env` / файл токена + предпочтительно hash в БД; UI-ротация предпочтительнее.

## 3. Проверка в web UI

1. Откройте `https://bad.example.com/devices` (после входа)
2. Найдите hostname (badge здоровья: **OK**, если last seen в пределах stale-порога, иначе **stale**)
3. Откройте карточку устройства: теги, недавние события изменений, последний inventory JSON
4. Опционально: **События** (`/events`) — лог изменений по всем устройствам (новее сверху)

Теги: правка на странице устройства (через запятую). Фильтр списка устройств по тегу. Политики тоже могут матчить `tag equals/contains`.

Master-ключи (`/etc/bad/data_key`, `/etc/bad/session_secret`) не входят в daily SQLite backup — храните escrow отдельно (в **site bundle** 0.10 они уже есть). Порог stale по умолчанию 1 час (`BAD_DEVICE_STALE_AFTER_SECONDS`); поставьте ≈2× heartbeat, если удобнее (напр. `1800` при heartbeat 15 мин). Версия продукта **0.10.0**.

Альтернатива (автоматизация — admin API token):

```bash
curl -fsS -H "Authorization: Bearer <admin-token>" \
  https://bad.example.com/v1/devices
curl -fsS -H "Authorization: Bearer <admin-token>" \
  'https://bad.example.com/v1/events?limit=50'
```

## 4. Обновления агента: upload MSI и выбор версии (0.10)

Страница: **Параметры → Обновления агента** (`/settings/updates`). Каталог на диске: `BAD_AGENT_UPDATES_DIR/{version}/bad-agent-{version}.msi` (+ `agent-release.json`). Агенты качают только с этого сервера; цель версии — knob `update_target` в политиках.

### Загрузить MSI (air-gap)

1. Откройте `/settings/updates`.
2. Секция **«Загрузить MSI (air-gap)»**: выберите файл MSI (`bad-agent-X.Y.Z.msi`), опционально manifest JSON, поля «Версия» / «SHA256» (sha можно не указывать — посчитаем).
3. **Подгрузить в зеркало**.
4. В **«Каталог версий»** появятся версия / файл / источник (`upload`\|`github`) / sha / время. Кнопки у строки: **Latest** (назначить указатель latest), **Удалить** (нельзя снести latest или версию под pin политики).

GitHub: **«Синхронизировать сейчас»** (`POST /settings/updates/sync`). Статус latest и интервал sync — в meta вверху страницы.

### «Последняя» vs pin (`update_target`)

| Значение в UI политик | Поведение |
|-----------------------|-----------|
| `latest (последняя в зеркале)` | target = site latest. Кнопка **Latest** на более старой версии → агенты с `latest` **downgrade**. |
| конкретная `X.Y.Z` из списка зеркала | pin; save на несуществующую версию отклоняется. Нет файла → агент no-op; на Обзоре — «Закреплённая версия отсутствует в зеркале». |

Где задать: **Параметры → Политики** (`update_target` в форме) или override на карточке устройства. Канон — `update_target` (алиас `desired_agent_version`). `update_enabled=false` — агент MSI не ставит. Агент следует `update_available` с сервера (upgrade и downgrade).

## 5. Site backup / restore (0.10)

Daily SQLite (`/var/lib/bad/backups/bad-YYYY-MM-DD.db`) **остаётся**. Отдельно — **Site bundle**.

**Скачать:** **Параметры → Резервные копии** → ссылка **«Скачать site bundle (.tar.gz)»** (`GET /settings/backups/site-bundle`). В архиве: DB + keys + meta зеркала; MSI по умолчанию не тащатся (объём). Секреты только в файле, не в HTML. Храните tar в сейфе.

**Restore (drill):**

```bash
sudo bash deploy/debian/restore-site-bundle.sh /path/to/bad-site-bundle-….tar.gz
```

Скрипт (root): останавливает `bad-api`, перезаписывает `/var/lib/bad/bad.db` и ключи в `/etc/bad`, поднимает сервис. Перед боем — пробный прогон на копии. После: `curl -fsS https://…/v1/health`, login, `/settings/updates` (доложить MSI upload’ом, если бинарников не было в bundle).

## 6. Ops-блок на Обзоре (0.10)

На **`/` / `/overview`** помимо обычных счётчиков (в т.ч. **Устарел** / stale):

- пустое зеркало MSI / latest + число версий + время sync;
- **«Отстают от целевой версии»** (version drift);
- **«Закреплённая версия отсутствует в зеркале»** (broken pin);
- отозванные устройства не в архиве (нужен rotate-key / recovery).

Сигналы «куда смотреть», не marketing dashboard.

## Безопасность для операторов

Краткий чеклист (детали — [guideline.md](guideline.md), [architecture.md](architecture.md)).

### БД и бэкапы = секреты сайта (SEC-005)

**Fresh install (0.11+):** `deploy/debian/install.sh` кладёт master keys **вне SQLite**:

| Файл | Назначение | Права |
|------|------------|--------|
| `/etc/bad/data_key` | Fernet (SMTP/LDAP bind) | `440` `root:bad` |
| `/etc/bad/session_secret` | подпись cookie `bad_session` | `440` `root:bad` |

В `site.env`: `BAD_DATA_KEY_FILE` / `BAD_SESSION_SECRET_FILE` (сервис `prefer_external_secrets`). Daily backup БД **не** содержит эти ключи.

**Residual (legacy / lab / старые инстансы):** если ключи остались в `site_secrets` SQLite — копия `bad.db` или daily backup = полный компромисс SMTP/LDAP и session cookies.

**Права на БД и бэкапы (минимум):**

```bash
chown bad:bad /var/lib/bad/bad.db /var/lib/bad/bad.db-* 2>/dev/null || true
chmod 600 /var/lib/bad/bad.db
chown -R bad:bad /var/lib/bad/backups
chmod 700 /var/lib/bad/backups
chmod 600 /var/lib/bad/backups/bad-*.db

chown root:bad /etc/bad/data_key /etc/bad/session_secret
chmod 440 /etc/bad/data_key /etc/bad/session_secret
```

Не кладите бэкапы БД в общие шары/тикеты. Не коммитьте `/etc/bad/data_key` / `session_secret` и не кладите их в тот же tar, что и `bad.db`.

### Cookie и TLS

До managed cert (HTTP bootstrap) UI и CSRF работают по HTTP (`BAD_COOKIE_SECURE=auto` + `X-Forwarded-Proto: http`). После upload+reload — только HTTPS через nginx (HSTS, redirect 80→443), cookie `Secure` без ожидания restart API. Site-bundle и сохранение LDAP/SMTP пароля по HTTP — 403 (lab: `BAD_ALLOW_SENSITIVE_OVER_HTTP=1`). При активном managed TLS cleartext `/v1/enroll` — 403 (lab: `BAD_ALLOW_ENROLL_OVER_HTTP=1`). Не открывайте uvicorn наружу. Агентов на HTTP bootstrap не направляйте.

### Enrollment token (SEC-011)

Не шарьте msiexec-логи / transcript’ы. После волны MSI — [ротация enrollment token](#ротация-enrollment-token-после-волны-msi) (UI в **0.10**).

## Заметки

- Апгрейд MSI сохраняет ProgramData (API key); повторный enroll не нужен.
- Не кладите enrollment или admin tokens в world-readable файлы.
- Локальные демо без TLS: uvicorn на Linux (`server/README.md`) и тестовый агент с `BAD_ALLOW_HTTP=1` на `http://127.0.0.1:8000` — только lab.

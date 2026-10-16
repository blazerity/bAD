# Операторский гайд — bAD

Путь end-to-end: установить сервер → поставить Windows MSI агента → увидеть устройство в web UI.

### Стабильность боя (обязательно)

| # | Правило | Детали |
|---|---------|--------|
| 1 | **Cert из панели — канон** | Install **без** `BAD_TLS_CERT`/`BAD_TLS_KEY` → HTTP bootstrap → загрузка PEM в **Параметры → Сертификат**. Cert при install — только shortcut, не обязанность. |
| 2 | **Дамп / daily backup БД ≠ ключи** | `pg_dump` **не** содержит `/etc/bad/data_key` и `session_secret`. Для DR — site bundle или отдельный escrow ключей. |
| 3 | **После волны MSI — ротация enrollment** | Сменить site token **обязательно** ([runbook](#ротация-enrollment-token-после-волны-msi)); обновить Intune/GPO; не шарить msiexec-логи. |

БД: **только Postgres** (`BAD_DATABASE_URL` в `site.env`). HA / ACME — вне scope. Ключи всегда в `/etc/bad/*`, вне БД.

## 1. Сервер (Debian 12)

**Канон (panel-first):** install без TLS-файлов → cert в UI. `BAD_TLS_*` при install — shortcut, не обязанность.

### БД: Postgres

- Единственный runtime: **`BAD_DATABASE_URL`** (libpq URL) в `site.env` (`640` root:bad). Без URL API не стартует.  
- Fresh `install.sh` поднимает **local Postgres** (role/db + schema), пишет URL, listen **localhost only**.  
- Lab/dev — тоже Postgres (local/docker), тем же env. Remote URL допустим тем же `BAD_DATABASE_URL`.  
- API/web **не** ветвятся: один контракт `/v1`.

### Этапы one-liner (`install.sh`)

Скрипт печатает `[1/6]…[6/6]`:

1. Пакеты (+ `postgresql` / `postgresql-client`)  
2. Пользователь / каталоги / venv  
3. БД (local PG + schema, `BAD_DATABASE_URL`)  
4. systemd `bad-api` (+ tls-apply)  
5. nginx  
6. Готово → **памятка** «что дальше»

Полный текст памятки — в хвосте install (не дублируем здесь). Дальше — чеклист bootstrap и [ротация](#ротация-enrollment-token-после-волны-msi).

### Install без cert → загрузка в панели (канон)

`BAD_TLS_CERT` / `BAD_TLS_KEY` **не обязательны**. Без них nginx — HTTP-only (:80), без HSTS и без 301 на HTTPS, пока не появится managed cert. Enter на prompt install = «позже из UI».

```bash
BAD_DOMAIN=bad.example.com \
  sudo -E bash deploy/debian/install.sh
# → UI: http://bad.example.com/  (пока нет сертификата)
```

Порядок (детали — [чеклист](#чеклист-окна-http-bootstrap)):

1. Откройте **`http://bad.example.com/login`** **только** из доверенного контура (LAN / VPN / `ssh -L`).
2. Войдите `admin` / `admin`, **сразу смените пароль**.
3. Загрузите cert+key: [§ Сертификат из панели](#сертификат-tls-из-панели) → «Установить и перезагрузить nginx».
4. Откройте **`https://…`**, **войдите заново**.
5. Только потом — enrollment / волна MSI (`https://…` в `SERVERURL`).
6. После волны — [ротация enrollment](#ротация-enrollment-token-после-волны-msi) (**обязательно**).

### Install сразу с TLS (shortcut)

Если cert уже на диске и так удобнее — можно передать пути (CN/SAN = `BAD_DOMAIN`). Это **не** отменяет panel-first как основной путь.

```bash
BAD_DOMAIN=bad.example.com \
BAD_TLS_CERT=/etc/ssl/certs/bad.fullchain.pem \
BAD_TLS_KEY=/etc/ssl/private/bad.privkey.pem \
  sudo -E bash deploy/debian/install.sh
```

Скрипт один раз печатает URL (`https://…`), enrollment token и admin API token. Дальше — [вход](#вход-в-web-локальный) по HTTPS.

#### Чеклист окна HTTP bootstrap

Временный UI до managed cert — **нормальный** боевой путь, не «обход». **Risk: Medium** на доверенной сети + короткое окно; **High** если `:80` публично до apply.

| # | Действие | Статус |
|---|----------|--------|
| 1 | Доступ к `:80` **только** из доверенного контура. **Не** публиковать панель в интернет до cert. | ☐ |
| 2 | Войти `admin` / `admin` → **сразу** сменить пароль (`/account/password`). | ☐ |
| 3 | Загрузить cert+key на **Параметры → Сертификат** → «Установить и перезагрузить nginx». | ☐ |
| 4 | Открыть **`https://…`**, **войти заново**. | ☐ |
| 5 | **Не** ставить MSI / агентов, пока режим «HTTP bootstrap». | ☐ |
| 6 | **Не** по HTTP: site-bundle, LDAP/SMTP с боевыми паролями, ротация enrollment «впрок», массовый enroll. | ☐ |
| 7 | После волны MSI — [ротация enrollment](#ротация-enrollment-token-после-волны-msi). | ☐ |

Проверка health:

```bash
curl -fsS http://bad.example.com/v1/health   # bootstrap без cert
curl -fsS https://bad.example.com/v1/health  # после TLS / с cert при install
# → {"status":"ok","version":"1.0.1"}
```

### Вход в web (локальный)

1. Откройте URL из вывода install (`http://…/login` при bootstrap или `https://…/login`).
2. Войдите локальным аккаунтом по умолчанию: **`admin` / `admin`**
3. **Сразу смените пароль** (`Пароль` в шапке / `/account/password`). До смены сервер пускает только `/account/password` и `/logout` (навигация скрыта). Не публикуйте UI за пределы доверенной сети, пока пароль не сменён.

Работает **без настроенного LDAP**. Admin API token для браузерного UI **не** используется.

Токены лежат в `/etc/bad/site.env` (режим `640`, `root:bad`). uvicorn — только `127.0.0.1:8000`; TLS терминирует **nginx** (не uvicorn). См. [Безопасность](#безопасность-для-операторов).

### Сертификат TLS из панели

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

Ручной retry apply: `systemctl start bad-tls-apply.service` (логи: `journalctl -u bad-tls-apply`). Let’s Encrypt / ACME нет. Смена `BAD_DOMAIN` из UI — вне scope.

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

Bind password хранится в БД зашифрованным и после save больше не показывается (оставьте поле пустым, чтобы не менять).

**TLS к LDAP (SEC-003):** по умолчанию LDAPS/StartTLS с `CERT_REQUIRED` (system CA или свой). Lab opt-in: флаг `tls_insecure` в настройках LDAP — только для лаборатории, не для боевого AD через недоверенную сеть.

## 2. Windows-агент (MSI)

На Windows build-хосте соберите MSI (см. `installer/msi/README.md`), затем установите:

```powershell
msiexec /i bad-agent-1.0.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  /qn
```

Опциональный PATH для локального CLI `bad` (по умолчанию выкл.):

```powershell
msiexec /i bad-agent-1.0.1.msi `
  SERVERURL=https://bad.example.com `
  ENROLLMENTTOKEN=<enrollment-token-from-install> `
  ADDPATH=1 `
  /qn
```

**Enrollment token (SEC-011):** deferred custom action читает token из HKLM `SOFTWARE\blazerity\bAD\Setup` и сразу удаляет ключ — **не** из argv PowerShell. Residual risk: родительский `msiexec … ENROLLMENTTOKEN=` (process command line) и verbose/`msiexec` логи / transcript’ы деплоя. Не пересылайте их. После волны установки **ротируйте** enrollment token (runbook ниже). Property `Hidden=yes` снижает утечку в UI MSI, но не убирает exposure в командной строке родителя. Подробнее: `installer/msi/README.md`.

**Если установка падает до появления логов агента** (пустой `%ProgramData%\blazerity\bAD\logs`, диалог MSI 1722): смотрите `%ProgramData%\blazerity\bAD\logs\msi-install.log` / `msi-ca-error.txt` (коды `BAD_MSI_###`) и `%TEMP%\MSI*.log`. Подробности: `installer/msi/README.md` → «Логи установки».

Служба `BlazerityAssetDiscovery` стартует автоматически, один раз enroll'ится, сохраняет API key в `%ProgramData%\blazerity\bAD\config.json` и шлёт inventory при старте (далее каждые 6 часов), heartbeat каждые 15 минут. Также спрашивает сервер про MSI-обновления (никогда не GitHub напрямую). Локальный CLI (сервер не нужен): `bad` / `bad -r` (HTML) / `bad -c` (настройка) / `bad -h` (справка). На карточке устройства метка **«задано на агенте»** = knobs с машины (`agent_local`), не политика и не server override. Service CLI: `BadAgent.exe service status|start|stop|restart` (elevated). См. [agents.md](./agents.md).

### Ротация enrollment token (после волны MSI)

**Обязательно** после массовой установки MSI (и если token мог утечь: логи в тикет, скрипт деплоя в общем репо). Пока site token жив, им можно enroll’ить новых агентов; residual `msiexec … ENROLLMENTTOKEN=` / verbose-логи ротацией **прошлого** не стираются — она закрывает **дальнейший** enroll старым token.

Уже зарегистрированные устройства **не** переустанавливать: у них API key в ProgramData. Ротацию и показ нового token делайте **по HTTPS** (после cert из панели).

**Шаги (UI):**

1. Войдите как локальный **admin** (или LDAP admin).
2. Откройте **Параметры → Обновления агента** (`/settings/updates`) — секция **Enrollment token** (текущий plaintext не показывается).
3. При желании — «Свой токен» (пусто = сервер сгенерирует).
4. **Сменить enrollment token**, подтвердите («Старый перестанет работать»).
5. Скопируйте **новый** token (показать один раз) в сейф. Restart `bad-api` не нужен.
6. Обновите Intune / GPO / следующие `msiexec` на новый `ENROLLMENTTOKEN=…`. Не шарьте `/l*v` и transcript’ы деплоя.

Автоматизация: `POST /v1/admin/enrollment/rotate` (admin Bearer) — plaintext один раз. Форма: `POST /settings/enrollment/rotate` (CSRF).

**После ротации:** старый Bearer → 401 на `/v1/enroll`; агенты с api_key продолжают работу. Revoke/rotate **API key** устройства — отдельная операция. Машина, не успевшая enroll со старым token, — MSI заново с новым `ENROLLMENTTOKEN`.

## 3. Проверка в web UI

1. Откройте `https://bad.example.com/devices` (после входа)
2. Найдите hostname (badge здоровья: **OK**, если last seen в пределах stale-порога, иначе **stale**)
3. Откройте карточку устройства: теги, недавние события изменений, последний inventory JSON
4. Опционально: **События** (`/events`) — лог изменений по всем устройствам (новее сверху)

Теги: правка на странице устройства (через запятую). Фильтр списка устройств по тегу. Политики тоже могут матчить `tag equals/contains`.

Daily DB backup **не** содержит master-ключи — см. [§ backup](#5-site-backup--restore). Порог stale по умолчанию 1 час (`BAD_DEVICE_STALE_AFTER_SECONDS`); ≈2× heartbeat при необходимости. Версия продукта **1.0.1**.

Альтернатива (автоматизация — admin API token):

```bash
curl -fsS -H "Authorization: Bearer <admin-token>" \
  https://bad.example.com/v1/devices
curl -fsS -H "Authorization: Bearer <admin-token>" \
  'https://bad.example.com/v1/events?limit=50'
```

## 4. Обновления агента: upload MSI и выбор версии

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

## 5. Site backup / restore

Три разных артефакта (не путать). **Дамп БД ≠ ключи.**

| Артефакт | Содержимое | Роль |
|----------|------------|------|
| **Daily DB** | `pg_dump -Fc` → `bad-YYYY-MM-DD.dump` в `BAD_BACKUP_DIR` (keep ≈ сегодня+вчера) | данные сайта; **не** полный DR без keys |
| **Key escrow** | `/etc/bad/data_key` + `session_secret` | отдельно от dump; `440` root:bad |
| **Site bundle** | **`bad.dump`** (`-Fc`) + keys + meta зеркала | полный DR; MSI опционально |

**Не** бэкапить копированием PG data directory. Restore: `pg_restore` из `bad.dump` (`restore-site-bundle.sh`).

**Скачать bundle:** **Параметры → Резервные копии** → **«Скачать site bundle»** — **только по HTTPS**.

**Escrow ключей (ops), без DB:**

```bash
sudo install -d -m 700 /root/bad-key-escrow
sudo tar -C /etc/bad -czf /root/bad-key-escrow/bad-keys-$(date -u +%Y%m%d).tar.gz data_key session_secret
sudo chmod 600 /root/bad-key-escrow/*
```

**Restore (drill) — канон через bundle:**

```bash
sudo bash deploy/debian/restore-site-bundle.sh /path/to/bad-site-bundle-….tar.gz
```

Скрипт (root): stop `bad-api` → `pg_restore` dump + keys в `/etc/bad` → start. Перед боем — пробный прогон. После: health, login, при необходимости MSI в `/settings/updates`.

## 6. Ops-блок на Обзоре

На **`/` / `/overview`** помимо обычных счётчиков (в т.ч. **Устарел** / stale):

- пустое зеркало MSI / latest + число версий + время sync;
- **«Отстают от целевой версии»** (version drift);
- **«Закреплённая версия отсутствует в зеркале»** (broken pin);
- отозванные устройства не в архиве (нужен rotate-key / recovery).

Сигналы «куда смотреть», не marketing dashboard.

## API / интеграция

Внешние системы (в т.ч. **1C Itilium**) читают данные bAD по HTTP JSON API `/v1` с **admin Bearer** — не через cookie web UI и не через agent API key.

Полный интеграционный гайд (base URL, auth, какие эндпоинты для 1C / какие только для агента, пагинация, ошибки, примеры curl, политика additive freeze): **[api-v1.md](api-v1.md)**.

Admin token печатается при install и лежит в `/etc/bad/site.env` (`BAD_ADMIN_TOKEN`). В бою вызывайте API только по **HTTPS**.

## Безопасность для операторов

Краткий чеклист (детали — [guideline.md](guideline.md), [architecture.md](architecture.md)).

### БД и бэкапы (SEC-005): DB ≠ ключи

**Fresh install:** keys **вне** БД — `/etc/bad/data_key` + `/etc/bad/session_secret` (`440` root:bad); пути в `site.env`.

| Что | Полный restore? |
|-----|-----------------|
| Daily `pg_dump -Fc` | **Нет** — без файлов ключей нет SMTP/LDAP decrypt и сессий |
| Key escrow | Нужен вместе с dump (или bundle) |
| Site bundle | **Да** — dump + keys (+ meta); хранить как секрет |

**Legacy:** если ключи ещё в таблице `site_secrets` (а не в `/etc/bad/*`) — любой dump БД = полный компромисс. Не смягчать.

Права: dumps/`backups` — `600`/`700` owner `bad`; keys — `440` `root:bad`. Не шарить dump-бэкапы и не коммитить `/etc/bad/*`.

### Cookie и TLS

Panel-first: до cert UI на HTTP (`BAD_COOKIE_SECURE=auto`). После apply — HTTPS, HSTS, cookie `Secure`. Site-bundle / LDAP/SMTP password / enrollment rotate — **по HTTPS** (на HTTP bootstrap — 403; lab-флаги в guideline). Агентов на HTTP не направлять.

### Enrollment token (SEC-011)

После волны MSI ротация **обязательна**. Не шарьте msiexec-логи / transcript’ы. Residual cmdline родителя ротацией не исчезает — см. [runbook](#ротация-enrollment-token-после-волны-msi).

## Заметки

- Апгрейд MSI сохраняет ProgramData (API key); повторный enroll не нужен.
- Не кладите enrollment или admin tokens в world-readable файлы.
- Локальные демо без TLS: uvicorn на Linux (`server/README.md`) и тестовый агент с `BAD_ALLOW_HTTP=1` на `http://127.0.0.1:8000` — только lab.
